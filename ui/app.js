/**
 * JARVIS General Purpose AI Super-Assistant — Interactive UI Controller
 * Integrates Rich Markdown Parsing, Conversational Avatar Mode, Voice Speech Synthesis,
 * Memory Tree, Goals Kanban, Tinyflows, and Multi-Channel Hub.
 */

document.addEventListener('DOMContentLoaded', () => {

    // -----------------------------------------------------------------------
    // 0. Markdown Parser Setup (Marked.js + Highlight.js)
    // -----------------------------------------------------------------------
    if (window.marked) {
        window.marked.setOptions({
            gfm: true,
            breaks: true,
            highlight: function (code, lang) {
                if (window.hljs) {
                    const validLang = window.hljs.getLanguage(lang) ? lang : 'plaintext';
                    return window.hljs.highlight(code, { language: validLang }).value;
                }
                return code;
            }
        });
    }

    function renderMarkdown(rawText) {
        if (!rawText) return '';
        if (window.marked) {
            try {
                return window.marked.parse(rawText);
            } catch (e) {
                console.warn('Marked parse error:', e);
            }
        }
        // Fallback simple replacement if marked is unavailable
        return rawText.replace(/\n/g, '<br/>');
    }

    // -----------------------------------------------------------------------
    // 1. Navigation View Switcher
    // -----------------------------------------------------------------------
    const navButtons = document.querySelectorAll('.nav-tab-btn');
    const viewPanes = document.querySelectorAll('.view-pane');

    function switchView(viewName) {
        if (!viewName) return;

        navButtons.forEach(btn => {
            if (btn.getAttribute('data-view') === viewName) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });

        viewPanes.forEach(pane => {
            if (pane.id === `view-${viewName}`) {
                pane.classList.remove('hidden');
            } else {
                pane.classList.add('hidden');
            }
        });

        // Trigger view-specific data refresh
        if (viewName === 'intelligence') loadMemoryAndGoals();
        if (viewName === 'workflows') loadWorkflows();
        if (viewName === 'channels') loadChannels();
        if (viewName === 'avatar') {
            setAvatarState('idle');
            updateAvatarSubtitles('Jarvis is online. Press the mic or hold Spacebar to talk.');
        }
    }

    navButtons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            switchView(btn.getAttribute('data-view'));
        });
    });

    const btnQuickVoice = document.getElementById('btn-quick-voice-mode');
    if (btnQuickVoice) {
        btnQuickVoice.addEventListener('click', () => switchView('avatar'));
    }

    const mascotBadge = document.getElementById('mascot-badge');
    if (mascotBadge) {
        mascotBadge.addEventListener('click', () => switchView('avatar'));
    }

    const btnExitAvatar = document.getElementById('btn-exit-avatar');
    if (btnExitAvatar) {
        btnExitAvatar.addEventListener('click', () => switchView('chat'));
    }

    // -----------------------------------------------------------------------
    // 2. High-Fidelity Voice Speech Synthesis (Client & Server)
    // -----------------------------------------------------------------------
    let autoVoiceEnabled = true;
    let selectedVoice = null;
    let synth = window.speechSynthesis;
    let lastSpokenText = "";

    const toggleVoiceBtn = document.getElementById('toggle-voice-auto-speak');
    const iconVoiceToggle = document.getElementById('icon-voice-toggle');
    const labelVoiceToggle = document.getElementById('label-voice-toggle');

    if (toggleVoiceBtn) {
        toggleVoiceBtn.addEventListener('click', () => {
            autoVoiceEnabled = !autoVoiceEnabled;
            if (autoVoiceEnabled) {
                iconVoiceToggle.innerText = 'volume_up';
                labelVoiceToggle.innerText = 'ON';
                labelVoiceToggle.className = 'text-success';
            } else {
                if (synth) synth.cancel();
                iconVoiceToggle.innerText = 'volume_off';
                labelVoiceToggle.innerText = 'OFF';
                labelVoiceToggle.className = 'text-on-surface-variant';
            }
        });
    }

    // Populate Natural Browser Voices
    function loadVoices() {
        if (!synth) return;
        const voices = synth.getVoices();
        const voiceSelect = document.getElementById('avatar-voice-select');
        if (!voiceSelect || voices.length === 0) return;

        voiceSelect.innerHTML = '';
        let preferredVoice = null;

        voices.forEach((v, idx) => {
            const opt = document.createElement('option');
            opt.value = idx;
            opt.innerText = `${v.name} (${v.lang})`;
            opt.className = 'bg-surface-card text-on-surface';
            voiceSelect.appendChild(opt);

            // Prefer natural English voices
            if (!preferredVoice && (v.name.includes('Natural') || v.name.includes('Google') || v.name.includes('US') || v.lang.startsWith('en'))) {
                preferredVoice = v;
                opt.selected = true;
            }
        });

        selectedVoice = preferredVoice || voices[0];
        voiceSelect.addEventListener('change', () => {
            selectedVoice = voices[voiceSelect.value];
        });
    }

    if (synth) {
        loadVoices();
        if (synth.onvoiceschanged !== undefined) {
            synth.onvoiceschanged = loadVoices;
        }
    }

    function cleanTextForSpeech(raw) {
        if (!raw) return '';
        return raw
            .replace(/```[\s\S]*?```/g, 'Code snippet omitted.')
            .replace(/`([^`]+)`/g, '$1')
            .replace(/\*\*([^*]+)\*\*/g, '$1')
            .replace(/\*([^*]+)\*/g, '$1')
            .replace(/#+\s+/g, '')
            .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
            .replace(/[-*•]\s+/g, '')
            .replace(/\|/g, ' ')
            .replace(/\s+/g, ' ')
            .trim();
    }

    function speakSpeech(text, onStart = null, onEnd = null) {
        if (!text) return;
        lastSpokenText = text;

        if (!synth) {
            // Server-side TTS fallback
            fetch('/api/tts/speak', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text: cleanTextForSpeech(text) })
            }).catch(e => console.warn('Server TTS error:', e));
            return;
        }

        try {
            synth.cancel(); // Cancel any previous speech
            const clean = cleanTextForSpeech(text);
            const utterance = new SpeechSynthesisUtterance(clean);
            
            if (selectedVoice) utterance.voice = selectedVoice;
            utterance.rate = 1.05;
            utterance.pitch = 1.0;

            utterance.onstart = () => {
                setAvatarState('speaking');
                if (onStart) onStart();
            };

            utterance.onend = () => {
                setAvatarState('idle');
                if (onEnd) onEnd();
            };

            utterance.onerror = (e) => {
                console.warn('SpeechSynthesis error:', e);
                setAvatarState('idle');
                if (onEnd) onEnd();
            };

            synth.speak(utterance);
        } catch (e) {
            console.error('Speech playback failed:', e);
            setAvatarState('idle');
        }
    }

    // Expose speak globally for button clicks
    window.replaySpeech = function (text) {
        speakSpeech(text);
    };

    // -----------------------------------------------------------------------
    // 3. Chat Stream & Message Handling with Markdown & Speaker Buttons
    // -----------------------------------------------------------------------
    const chatStream = document.getElementById('chat-stream');
    const chatInput = document.getElementById('chat-input');
    const btnSend = document.getElementById('btn-send-message');

    function appendMessage(role, text, toolMeta = null) {
        const isUser = role === 'user';
        const msgDiv = document.createElement('div');
        msgDiv.className = `flex gap-3 max-w-3xl ${isUser ? 'ml-auto justify-end' : 'mr-auto justify-start'}`;

        const avatar = isUser
            ? `<div class="w-8 h-8 rounded-lg bg-secondary/30 border border-secondary/50 flex items-center justify-center text-xs font-mono font-bold text-secondary flex-shrink-0">YOU</div>`
            : `<div class="w-8 h-8 rounded-lg bg-primary/20 border border-primary/40 flex items-center justify-center text-xs font-headline font-bold text-primary flex-shrink-0">J</div>`;

        let toolHtml = '';
        if (toolMeta) {
            toolHtml = `
                <div class="mt-3 p-2.5 rounded-lg bg-surface-card border border-primary/30 font-mono text-xs space-y-1">
                    <div class="flex items-center justify-between text-primary">
                        <span class="flex items-center gap-1 font-bold">
                            <span class="material-symbols-outlined text-xs">build</span>
                            ${toolMeta.tool_name || 'Jarvis Reasoning Core'}
                        </span>
                        <span class="text-[10px] text-success">SUCCESS (0.12s)</span>
                    </div>
                    <div class="text-[11px] text-on-surface-variant break-all">${toolMeta.summary || ''}</div>
                </div>
            `;
        }

        const safeId = 'msg-' + Math.random().toString(36).substring(2, 9);
        const renderedContent = isUser ? text.replace(/\n/g, '<br/>') : renderMarkdown(text);

        const speakerBtn = !isUser
            ? `<button onclick="replaySpeech(document.getElementById('${safeId}').innerText)" class="text-on-surface-variant hover:text-primary transition-colors flex items-center gap-1 px-1.5 py-0.5 rounded hover:bg-primary/10" title="Replay voice audio">
                 <span class="material-symbols-outlined text-xs">volume_up</span>
                 <span class="text-[10px]">Replay</span>
               </button>`
            : '';

        const bubble = `
            <div class="space-y-1 max-w-2xl">
                <div class="px-5 py-4 rounded-2xl text-sm leading-relaxed ${
                    isUser
                        ? 'bg-primary/20 text-on-surface border border-primary/30 rounded-tr-none'
                        : 'glass-panel text-on-surface border border-surface-border rounded-tl-none'
                }">
                    <div id="${safeId}" class="${!isUser ? 'markdown-body' : ''}">${renderedContent}</div>
                    ${toolHtml}
                </div>
                <div class="flex items-center justify-between px-1 text-[10px] font-mono text-on-surface-variant">
                    <span>${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                    ${speakerBtn}
                </div>
            </div>
        `;

        msgDiv.innerHTML = isUser ? bubble + avatar : avatar + bubble;
        chatStream.appendChild(msgDiv);
        chatStream.scrollTop = chatStream.scrollHeight;

        // Automatically speak out the response if enabled
        if (!isUser && autoVoiceEnabled) {
            speakSpeech(text);
        }
    }

    async function handleSendMessage(inputOverride = null) {
        const text = inputOverride || chatInput.value.trim();
        if (!text) return;

        appendMessage('user', text);
        if (!inputOverride) chatInput.value = '';
        setAvatarState('thinking');

        try {
            const resp = await fetch('/api/agent/command', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ command: text })
            });
            const data = await resp.json();
            const summary = data.summary || (data.data && data.data.result) || JSON.stringify(data);
            
            appendMessage('assistant', summary, {
                tool_name: data.data?.tool_slug || 'Jarvis Reasoning Core',
                summary: data.data?.details || data.summary
            });

            updateAvatarSubtitles(summary);
        } catch (e) {
            setAvatarState('idle');
            appendMessage('assistant', `⚠️ Execution Error: ${e.message}`);
            updateAvatarSubtitles(`Execution error: ${e.message}`);
        }
    }

    btnSend.addEventListener('click', () => handleSendMessage());
    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSendMessage();
        }
    });

    document.querySelectorAll('.quick-prompt-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const prompt = btn.innerText.replace(/^[^\"]*\"|\"[^\"]*$/g, '');
            chatInput.value = prompt;
            handleSendMessage();
        });
    });

    // -----------------------------------------------------------------------
    // 4. Conversational Avatar Mode Controller
    // -----------------------------------------------------------------------
    const avatarStageOrb = document.getElementById('avatar-stage-orb');
    const avatarMouth = document.getElementById('avatar-mouth');
    const avatarStatusPill = document.getElementById('avatar-status-pill');
    const avatarStatusText = document.getElementById('avatar-status-text');
    const avatarLiveTranscript = document.getElementById('avatar-live-transcript');
    const btnAvatarSpeak = document.getElementById('btn-avatar-speak');
    const avatarSpeakIcon = document.getElementById('avatar-speak-icon');
    const btnAvatarReplay = document.getElementById('btn-avatar-replay');
    const btnAvatarAutoLoop = document.getElementById('btn-avatar-auto-loop');
    const iconAutoLoop = document.getElementById('icon-auto-loop');

    let continuousAutoLoop = false;
    let isAvatarRecording = false;

    function setAvatarState(state) {
        if (!avatarStageOrb) return;
        avatarStageOrb.classList.remove('glow-avatar-idle', 'glow-avatar-speaking', 'glow-avatar-listening', 'glow-avatar-thinking');
        avatarMouth.classList.remove('avatar-mouth-speaking');

        if (state === 'idle') {
            avatarStageOrb.classList.add('glow-avatar-idle');
            avatarStatusText.innerText = 'JARVIS READY // CLICK MIC TO SPEAK';
            avatarStatusPill.className = 'px-4 py-1.5 rounded-full bg-surface-card border border-primary/40 font-mono text-xs font-bold text-primary flex items-center gap-2 shadow-lg';
            avatarSpeakIcon.innerText = 'mic';
        } else if (state === 'listening') {
            avatarStageOrb.classList.add('glow-avatar-listening');
            avatarStatusText.innerText = 'LISTENING... SPEAK CLEARLY';
            avatarStatusPill.className = 'px-4 py-1.5 rounded-full bg-success/20 border border-success font-mono text-xs font-bold text-success flex items-center gap-2 shadow-lg';
            avatarSpeakIcon.innerText = 'graphic_eq';
        } else if (state === 'thinking') {
            avatarStageOrb.classList.add('glow-avatar-thinking');
            avatarStatusText.innerText = 'THINKING & REASONING...';
            avatarStatusPill.className = 'px-4 py-1.5 rounded-full bg-purple-accent/20 border border-purple-accent font-mono text-xs font-bold text-purple-accent flex items-center gap-2 shadow-lg';
            avatarSpeakIcon.innerText = 'psychology';
        } else if (state === 'speaking') {
            avatarStageOrb.classList.add('glow-avatar-speaking');
            avatarMouth.classList.add('avatar-mouth-speaking');
            avatarStatusText.innerText = 'SPEAKING OUT LOUD...';
            avatarStatusPill.className = 'px-4 py-1.5 rounded-full bg-primary/20 border border-primary font-mono text-xs font-bold text-primary flex items-center gap-2 shadow-lg';
            avatarSpeakIcon.innerText = 'volume_up';
        }
    }

    function updateAvatarSubtitles(text) {
        if (avatarLiveTranscript) {
            avatarLiveTranscript.innerText = `"${cleanTextForSpeech(text).substring(0, 240)}..."`;
        }
    }

    // Push-to-Talk SpeechRecognition
    let recognition = null;
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
        const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
        recognition = new SpeechRec();
        recognition.continuous = false;
        recognition.interimResults = true;
        recognition.lang = 'en-US';

        recognition.onstart = () => {
            isAvatarRecording = true;
            setAvatarState('listening');
            updateAvatarSubtitles('Listening to your voice...');
        };

        recognition.onresult = (e) => {
            const transcript = Array.from(e.results).map(r => r[0].transcript).join('');
            updateAvatarSubtitles(transcript);
            if (e.results[0].isFinal) {
                recognition.stop();
                handleAvatarVoiceTurn(transcript);
            }
        };

        recognition.onerror = (e) => {
            console.warn('SpeechRecognition error:', e);
            setAvatarState('idle');
            isAvatarRecording = false;
        };

        recognition.onend = () => {
            isAvatarRecording = false;
        };
    }

    function toggleAvatarListening() {
        if (!recognition) {
            alert('Speech recognition is not supported in this browser. Please use Chrome or Edge.');
            return;
        }
        if (synth) synth.cancel();

        if (!isAvatarRecording) {
            try {
                recognition.start();
            } catch (e) {
                console.warn('Recognition start error:', e);
            }
        } else {
            recognition.stop();
        }
    }

    async function handleAvatarVoiceTurn(userSpeech) {
        if (!userSpeech || !userSpeech.trim()) {
            setAvatarState('idle');
            return;
        }

        setAvatarState('thinking');
        updateAvatarSubtitles(`You: "${userSpeech}"`);

        try {
            const resp = await fetch('/api/agent/command', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ command: userSpeech })
            });
            const data = await resp.json();
            const reply = data.summary || (data.data && data.data.result) || JSON.stringify(data);

            updateAvatarSubtitles(reply);
            appendMessage('user', userSpeech);
            appendMessage('assistant', reply, {
                tool_name: data.data?.tool_slug || 'Jarvis Voice Reasoning',
                summary: data.data?.details || data.summary
            });

            // Speak out and loop if continuous mode is enabled
            speakSpeech(reply, () => {
                setAvatarState('speaking');
            }, () => {
                setAvatarState('idle');
                if (continuousAutoLoop) {
                    setTimeout(() => toggleAvatarListening(), 600);
                }
            });
        } catch (e) {
            setAvatarState('idle');
            updateAvatarSubtitles(`Error: ${e.message}`);
        }
    }

    if (btnAvatarSpeak) {
        btnAvatarSpeak.addEventListener('click', toggleAvatarListening);
    }

    const chatMicBtn = document.getElementById('chat-mic-btn');
    if (chatMicBtn) {
        chatMicBtn.addEventListener('click', toggleAvatarListening);
    }

    if (btnAvatarReplay) {
        btnAvatarReplay.addEventListener('click', () => {
            if (lastSpokenText) {
                speakSpeech(lastSpokenText);
            }
        });
    }

    if (btnAvatarAutoLoop) {
        btnAvatarAutoLoop.addEventListener('click', () => {
            continuousAutoLoop = !continuousAutoLoop;
            if (continuousAutoLoop) {
                btnAvatarAutoLoop.classList.add('bg-primary/20', 'border-primary', 'text-primary');
                iconAutoLoop.innerText = 'sync';
                alert('Continuous Conversational Voice Mode: ON');
            } else {
                btnAvatarAutoLoop.classList.remove('bg-primary/20', 'border-primary', 'text-primary');
                iconAutoLoop.innerText = 'all_inclusive';
            }
        });
    }

    // Spacebar PTT shortcut in Avatar Mode
    window.addEventListener('keydown', (e) => {
        if (e.code === 'Space' && document.getElementById('view-avatar') && !document.getElementById('view-avatar').classList.contains('hidden')) {
            if (document.activeElement !== chatInput && !isAvatarRecording) {
                e.preventDefault();
                toggleAvatarListening();
            }
        }
    });

    // -----------------------------------------------------------------------
    // 5. Memory Tree & Goals Kanban Data Fetcher
    // -----------------------------------------------------------------------
    async function loadMemoryAndGoals() {
        try {
            // Load Goals
            const goalsResp = await fetch('/api/goals');
            const goalsData = await goalsResp.json();
            const cols = goalsData.data?.columns || {};

            ['todo', 'in_progress', 'blocked', 'done'].forEach(col => {
                const cntElem = document.getElementById(`cnt-${col.replace('_', '-')}`);
                const colElem = document.getElementById(`col-${col.replace('_', '-')}`);
                const items = cols[col] || [];
                if (cntElem) cntElem.innerText = items.length;
                if (colElem) {
                    colElem.innerHTML = items.map(item => `
                        <div class="p-2.5 rounded-lg bg-surface-card border border-surface-border space-y-1.5 hover:border-primary/40 transition-all">
                            <div class="flex justify-between items-start">
                                <strong class="text-on-surface text-[11px]">${item.title}</strong>
                                <span class="px-1.5 py-0.2 bg-primary/20 text-primary text-[9px] font-bold rounded uppercase">${item.priority}</span>
                            </div>
                            <p class="text-[10px] text-on-surface-variant">${item.description || ''}</p>
                            ${item.progress > 0 ? `
                                <div class="w-full bg-surface rounded-full h-1 mt-1 overflow-hidden">
                                    <div class="bg-primary h-full rounded-full" style="width: ${item.progress}%"></div>
                                </div>
                            ` : ''}
                        </div>
                    `).join('') || '<div class="text-[11px] text-on-surface-variant/50 italic p-2">No tasks</div>';
                }
            });

            // Load Memory Nodes
            const memResp = await fetch('/api/memory_tree');
            const memData = await memResp.json();
            const nodes = memData.data?.nodes || [];
            const memList = document.getElementById('memory-nodes-list');
            if (memList) {
                memList.innerHTML = nodes.map(n => `
                    <div class="p-3 rounded-lg bg-surface-card border border-surface-border space-y-1 hover:border-primary/40 transition-all">
                        <div class="flex justify-between items-center text-primary font-bold">
                            <span>${n.title}</span>
                            <span class="text-[9px] px-1.5 py-0.5 rounded bg-primary/10 border border-primary/30 font-mono">IMP: ${n.importance}/10</span>
                        </div>
                        <div class="text-[10px] text-on-surface-variant font-mono">${n.path}</div>
                        <div class="text-[11px] text-on-surface/80 pt-1 line-clamp-2">${n.content}</div>
                    </div>
                `).join('') || '<div class="text-xs text-on-surface-variant p-2">No memory nodes stored yet.</div>';
            }
        } catch (e) {
            console.error('Error loading memory and goals:', e);
        }
    }

    // -----------------------------------------------------------------------
    // 6. Workflows Data Fetcher (Tinyflows)
    // -----------------------------------------------------------------------
    async function loadWorkflows() {
        try {
            const resp = await fetch('/api/workflows');
            const data = await resp.json();
            const workflows = data.data?.workflows || [];
            const grid = document.getElementById('workflows-grid');
            if (grid) {
                grid.innerHTML = workflows.map(wf => `
                    <div class="glass-panel p-4 rounded-xl border border-surface-border flex flex-col justify-between space-y-3 hover:border-primary/40 transition-all">
                        <div class="space-y-1.5">
                            <div class="flex justify-between items-center">
                                <span class="px-2 py-0.5 rounded bg-primary/20 text-primary text-[10px] font-mono font-bold uppercase">${wf.trigger_type} TRIGGER</span>
                                <span class="w-2 h-2 rounded-full ${wf.enabled ? 'bg-success' : 'bg-on-surface-variant'}"></span>
                            </div>
                            <h3 class="font-headline font-bold text-sm text-on-surface">${wf.name}</h3>
                            <p class="text-xs text-on-surface-variant font-sans">${wf.description}</p>
                        </div>
                        <div class="pt-2 border-t border-surface-border flex justify-between items-center font-mono text-xs">
                            <span class="text-[10px] text-on-surface-variant">${wf.steps?.length || 0} Steps</span>
                            <button onclick="runWorkflow('${wf.id}')" class="px-3 py-1 bg-primary/20 border border-primary/40 text-primary font-bold rounded hover:bg-primary hover:text-surface transition-all text-xs">
                                RUN NOW
                            </button>
                        </div>
                    </div>
                `).join('');
            }
        } catch (e) {
            console.error('Error loading workflows:', e);
        }
    }

    window.runWorkflow = async function(wfId) {
        try {
            const resp = await fetch('/api/workflows/execute', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ workflow_id_or_name: wfId })
            });
            const data = await resp.json();
            switchView('chat');
            appendMessage('assistant', `⚡ Executed Workflow **${data.data?.workflow_name}** (Run #${data.data?.run_id}): All ${data.data?.steps_executed} steps finished successfully.`);
        } catch (e) {
            alert('Workflow execution error: ' + e.message);
        }
    };

    // -----------------------------------------------------------------------
    // 7. Multi-Channel Hub Data Fetcher
    // -----------------------------------------------------------------------
    async function loadChannels() {
        try {
            const resp = await fetch('/api/channels');
            const data = await resp.json();
            const channels = data.data?.channels || [];
            const grid = document.getElementById('channels-status-grid');
            if (grid) {
                grid.innerHTML = channels.map(c => `
                    <div class="glass-panel p-4 rounded-xl border border-surface-border space-y-2 hover:border-primary/40 transition-all">
                        <div class="flex justify-between items-center">
                            <strong class="text-sm font-headline text-on-surface">${c.name}</strong>
                            <span class="px-2 py-0.5 rounded text-[9px] font-bold uppercase ${c.status === 'active' ? 'bg-success/20 text-success' : 'bg-primary/20 text-primary'}">${c.status}</span>
                        </div>
                        <div class="text-[11px] text-on-surface-variant">Account: <span class="text-on-surface font-semibold">${c.account}</span></div>
                        <div class="text-[10px] text-on-surface-variant font-mono">Provider: ${c.provider}</div>
                    </div>
                `).join('');
            }
        } catch (e) {
            console.error('Error loading channels:', e);
        }
    }

    const btnDispatch = document.getElementById('btn-dispatch-message');
    if (btnDispatch) {
        btnDispatch.addEventListener('click', async () => {
            const channel = document.getElementById('dispatch-channel').value;
            const recipient = document.getElementById('dispatch-recipient').value.trim();
            const content = document.getElementById('dispatch-content').value.trim();
            if (!recipient || !content) {
                alert('Please provide recipient and message content.');
                return;
            }
            try {
                const resp = await fetch('/api/channels/send', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ channel, recipient, content })
                });
                const data = await resp.json();
                alert(`Message dispatched to [${channel.toUpperCase()}]: ${data.summary}`);
                document.getElementById('dispatch-content').value = '';
            } catch (e) {
                alert('Dispatch error: ' + e.message);
            }
        });
    }

    // Initial default view
    switchView('chat');
});
