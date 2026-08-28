/**
 * JARVIS Universal AI Super-Assistant — Interactive UI & Ghosty Mascot Controller
 * Inspired by OpenHuman (TinyHumans AI) architecture:
 * - Mathematical Viseme Lip-Sync & Quadratic Bezier Mouth Morpher
 * - Real-time Cursor-Tracking Pupils & Natural Blinking Physics
 * - Expressive Mascot Face Presets (idle, listening, thinking, speaking, happy, confused)
 * - Multi-Palette Reactive Shaders
 * - Marked.js Markdown Engine & Full-Duplex Voice Assistant
 */

document.addEventListener('DOMContentLoaded', () => {

    // =======================================================================
    // 0. MARKDOWN PARSER SETUP (Marked.js + Highlight.js)
    // =======================================================================
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
        return rawText.replace(/\n/g, '<br/>');
    }

    // =======================================================================
    // 1. OPENHUMAN GHOSTY MASCOT CONTROLLER & VISEME ENGINE
    // =======================================================================
    
    // Viseme Definitions (from OpenHuman math)
    const VISEMES = {
        REST: { openness: 0, width: 0.3 },
        A:    { openness: 0.95, width: 0.65 },
        E:    { openness: 0.45, width: 1.0 },
        I:    { openness: 0.3, width: 0.85 },
        O:    { openness: 0.8, width: 0.2 },
        U:    { openness: 0.45, width: 0.05 },
        M:    { openness: 0.02, width: 0.4 },
        F:    { openness: 0.18, width: 0.55 }
    };

    const REST_SMILE_PATH = 'M460,610 Q500,655 540,610 Q500,632 460,610 Z';
    const HAPPY_EYE_LEFT  = 'M390,525 Q420,490 450,525';
    const HAPPY_EYE_RIGHT = 'M550,525 Q580,490 610,525';

    function getVisemeSvgPath(shape) {
        if (shape.openness < 0.06) return REST_SMILE_PATH;
        const CX = 500;
        const CY = 615;
        const halfW = 20 + shape.width * 30;
        const halfH = 4 + shape.openness * 28;
        const left = CX - halfW;
        const right = CX + halfW;
        const top = CY - halfH;
        const bot = CY + halfH;
        return `M${left},${CY} Q${CX},${top} ${right},${CY} Q${CX},${bot} ${left},${CY} Z`;
    }

    class GhostyMascotController {
        constructor() {
            this.svg = document.getElementById('mascot-svg');
            this.mouth = document.getElementById('ghosty-mouth');
            this.eyeLeftSocket = document.getElementById('eye-left-socket');
            this.eyeRightSocket = document.getElementById('eye-right-socket');
            this.pupilLeft = document.getElementById('pupil-left');
            this.pupilRight = document.getElementById('pupil-right');
            this.brows = document.getElementById('ghosty-brows');
            this.browLeft = document.getElementById('brow-left');
            this.browRight = document.getElementById('brow-right');
            this.arm = document.getElementById('ghosty-arm');
            this.blushLeft = document.getElementById('ghosty-blush-left');
            this.blushRight = document.getElementById('ghosty-blush-right');
            this.gradAccentStop = document.getElementById('grad-accent-stop');
            this.eyeGlowStop = document.getElementById('eye-glow-stop');

            this.state = 'idle'; // idle, listening, thinking, speaking, happy, confused
            this.targetViseme = VISEMES.REST;
            this.currentViseme = { ...VISEMES.REST };
            this.visemeAnimTimer = null;
            this.blinkTimer = null;
            this.isBlinking = false;

            // Pupil Target Offsets
            this.targetPupilX = 0;
            this.targetPupilY = 0;
            this.currentPupilX = 0;
            this.currentPupilY = 0;

            this.init();
        }

        init() {
            // Setup Mouse Tracking for Cursor-Following Eyes
            window.addEventListener('mousemove', (e) => {
                if (!this.svg) return;
                const rect = this.svg.getBoundingClientRect();
                const centerX = rect.left + rect.width / 2;
                const centerY = rect.top + rect.height / 2;
                const dx = (e.clientX - centerX) / (window.innerWidth / 2);
                const dy = (e.clientY - centerY) / (window.innerHeight / 2);
                
                // Max pupil radius offset in SVG units
                this.targetPupilX = Math.max(-14, Math.min(14, dx * 14));
                this.targetPupilY = Math.max(-16, Math.min(16, dy * 16));
            });

            // Start Natural Blinking Loop
            this.scheduleNextBlink();

            // Start Continuous Animation Loop (RAF)
            this.renderLoop();

            // Setup Poke/Tickle Interaction
            const mascotBox = document.getElementById('mascot-stage-wrapper');
            if (mascotBox) {
                mascotBox.addEventListener('click', () => this.pokeMascot());
            }

            // Setup Color Palette Buttons
            document.querySelectorAll('.mascot-palette-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    const color = btn.getAttribute('data-color');
                    this.setPalette(color);
                });
            });
        }

        setPalette(hex) {
            if (this.gradAccentStop) this.gradAccentStop.setAttribute('stop-color', hex);
            if (this.eyeGlowStop) this.eyeGlowStop.setAttribute('stop-color', hex);
            const statusPill = document.getElementById('avatar-status-pill');
            if (statusPill) statusPill.style.borderColor = hex;
        }

        scheduleNextBlink() {
            const delay = 3000 + Math.random() * 3500;
            this.blinkTimer = setTimeout(() => {
                this.triggerBlink();
                this.scheduleNextBlink();
            }, delay);
        }

        triggerBlink() {
            if (this.state === 'happy') return;
            this.isBlinking = true;
            if (this.eyeLeftSocket && this.eyeRightSocket) {
                this.eyeLeftSocket.setAttribute('ry', '3');
                this.eyeRightSocket.setAttribute('ry', '3');
                if (this.pupilLeft) this.pupilLeft.style.opacity = '0';
                if (this.pupilRight) this.pupilRight.style.opacity = '0';
            }

            setTimeout(() => {
                this.isBlinking = false;
                this.updateEyeGeometry();
                if (this.pupilLeft) this.pupilLeft.style.opacity = '1';
                if (this.pupilRight) this.pupilRight.style.opacity = '1';
            }, 160);
        }

        pokeMascot() {
            this.setFaceMood('happy');
            if (this.arm) this.arm.classList.add('mascot-waving-arm');
            this.playChirpSound(620, 880);

            const pill = document.getElementById('avatar-status-text');
            if (pill) pill.innerText = "HEHE! JARVIS IS HAPPY TO SERVE YOU ✨";

            setTimeout(() => {
                if (this.arm) this.arm.classList.remove('mascot-waving-arm');
                this.setFaceMood(this.state);
            }, 2500);
        }

        playChirpSound(freq1, freq2) {
            try {
                const AudioCtx = window.AudioContext || window.webkitAudioContext;
                if (!AudioCtx) return;
                const ctx = new AudioCtx();
                const osc = ctx.createOscillator();
                const gain = ctx.createGain();
                osc.type = 'sine';
                osc.frequency.setValueAtTime(freq1, ctx.currentTime);
                osc.frequency.exponentialRampToValueAtTime(freq2, ctx.currentTime + 0.15);
                gain.gain.setValueAtTime(0.08, ctx.currentTime);
                gain.gain.linearRampToValueAtTime(0.001, ctx.currentTime + 0.2);
                osc.connect(gain);
                gain.connect(ctx.destination);
                osc.start();
                osc.stop(ctx.currentTime + 0.2);
            } catch (e) {
                // Audio context may be blocked before gesture
            }
        }

        setFaceMood(mood) {
            this.state = mood;
            const statusPill = document.getElementById('avatar-status-pill');
            const statusText = document.getElementById('avatar-status-text');
            const statusDot = document.getElementById('status-dot');
            const speakIcon = document.getElementById('avatar-speak-icon');

            if (mood === 'idle') {
                this.stopSpeakingVisemes();
                this.targetViseme = VISEMES.REST;
                if (this.brows) this.brows.style.opacity = '0';
                if (this.blushLeft) this.blushLeft.style.opacity = '0.4';
                if (this.blushRight) this.blushRight.style.opacity = '0.4';
                if (statusText) statusText.innerText = 'JARVIS READY // CLICK MIC OR SPACEBAR TO TALK';
                if (statusPill) statusPill.className = 'px-5 py-2 rounded-full bg-surface-card border border-primary/40 font-mono text-xs font-bold text-primary flex items-center gap-2.5 shadow-[0_0_20px_rgba(0,242,255,0.25)]';
                if (statusDot) statusDot.className = 'w-2.5 h-2.5 rounded-full bg-primary animate-ping';
                if (speakIcon) speakIcon.innerText = 'mic';
            } else if (mood === 'listening') {
                this.stopSpeakingVisemes();
                this.targetViseme = VISEMES.REST;
                if (this.brows) this.brows.style.opacity = '1';
                if (this.browLeft) this.browLeft.setAttribute('transform', 'translate(0, -12) rotate(-8 415 450)');
                if (this.browRight) this.browRight.setAttribute('transform', 'translate(0, -12) rotate(8 585 450)');
                if (this.blushLeft) this.blushLeft.style.opacity = '0.8';
                if (this.blushRight) this.blushRight.style.opacity = '0.8';
                if (statusText) statusText.innerText = 'LISTENING... SPEAK CLEARLY';
                if (statusPill) statusPill.className = 'px-5 py-2 rounded-full bg-success/20 border border-success font-mono text-xs font-bold text-success flex items-center gap-2.5 shadow-[0_0_30px_rgba(16,185,129,0.5)]';
                if (statusDot) statusDot.className = 'w-2.5 h-2.5 rounded-full bg-success animate-ping';
                if (speakIcon) speakIcon.innerText = 'graphic_eq';
            } else if (mood === 'thinking') {
                this.stopSpeakingVisemes();
                this.targetViseme = VISEMES.U;
                if (this.brows) this.brows.style.opacity = '1';
                if (this.browLeft) this.browLeft.setAttribute('transform', 'translate(0, -5) rotate(12 415 450)');
                if (this.browRight) this.browRight.setAttribute('transform', 'translate(0, -5) rotate(-12 585 450)');
                if (statusText) statusText.innerText = 'THINKING & REASONING (MEDULLA CORE)...';
                if (statusPill) statusPill.className = 'px-5 py-2 rounded-full bg-purple-accent/20 border border-purple-accent font-mono text-xs font-bold text-purple-accent flex items-center gap-2.5 shadow-[0_0_30px_rgba(168,85,247,0.6)]';
                if (statusDot) statusDot.className = 'w-2.5 h-2.5 rounded-full bg-purple-accent animate-ping';
                if (speakIcon) speakIcon.innerText = 'psychology';
            } else if (mood === 'speaking') {
                this.startSpeakingVisemes();
                if (this.brows) this.brows.style.opacity = '0.6';
                if (this.browLeft) this.browLeft.setAttribute('transform', 'translate(0, -8) rotate(-4 415 450)');
                if (this.browRight) this.browRight.setAttribute('transform', 'translate(0, -8) rotate(4 585 450)');
                if (this.blushLeft) this.blushLeft.style.opacity = '0.7';
                if (this.blushRight) this.blushRight.style.opacity = '0.7';
                if (statusText) statusText.innerText = 'SPEAKING OUT LOUD (VOICE SYNTHESIS)...';
                if (statusPill) statusPill.className = 'px-5 py-2 rounded-full bg-primary/20 border border-primary font-mono text-xs font-bold text-primary flex items-center gap-2.5 shadow-[0_0_35px_rgba(0,242,255,0.7)]';
                if (statusDot) statusDot.className = 'w-2.5 h-2.5 rounded-full bg-primary animate-ping';
                if (speakIcon) speakIcon.innerText = 'volume_up';
            } else if (mood === 'happy') {
                this.stopSpeakingVisemes();
                this.targetViseme = VISEMES.E;
                if (this.blushLeft) this.blushLeft.style.opacity = '1';
                if (this.blushRight) this.blushRight.style.opacity = '1';
            }

            this.updateEyeGeometry();
        }

        updateEyeGeometry() {
            if (this.isBlinking) return;
            if (!this.eyeLeftSocket || !this.eyeRightSocket) return;

            if (this.state === 'listening') {
                this.eyeLeftSocket.setAttribute('rx', '34');
                this.eyeLeftSocket.setAttribute('ry', '58');
                this.eyeRightSocket.setAttribute('rx', '34');
                this.eyeRightSocket.setAttribute('ry', '58');
            } else if (this.state === 'thinking') {
                this.eyeLeftSocket.setAttribute('rx', '26');
                this.eyeLeftSocket.setAttribute('ry', '38');
                this.eyeRightSocket.setAttribute('rx', '30');
                this.eyeRightSocket.setAttribute('ry', '48');
            } else {
                this.eyeLeftSocket.setAttribute('rx', '30');
                this.eyeLeftSocket.setAttribute('ry', '52');
                this.eyeRightSocket.setAttribute('rx', '30');
                this.eyeRightSocket.setAttribute('ry', '52');
            }
        }

        startSpeakingVisemes() {
            this.stopSpeakingVisemes();
            const visemeKeys = ['A', 'E', 'O', 'I', 'U', 'M', 'F'];
            let idx = 0;
            this.visemeAnimTimer = setInterval(() => {
                const key = visemeKeys[idx % visemeKeys.length];
                this.targetViseme = VISEMES[key];
                idx++;
            }, 120);
        }

        stopSpeakingVisemes() {
            if (this.visemeAnimTimer) {
                clearInterval(this.visemeAnimTimer);
                this.visemeAnimTimer = null;
            }
        }

        renderLoop() {
            // Smooth Pupil Damping (Lerp)
            this.currentPupilX += (this.targetPupilX - this.currentPupilX) * 0.12;
            this.currentPupilY += (this.targetPupilY - this.currentPupilY) * 0.12;

            if (this.pupilLeft) this.pupilLeft.setAttribute('cx', this.currentPupilX.toFixed(2));
            if (this.pupilLeft) this.pupilLeft.setAttribute('cy', this.currentPupilY.toFixed(2));
            if (this.pupilRight) this.pupilRight.setAttribute('cx', this.currentPupilX.toFixed(2));
            if (this.pupilRight) this.pupilRight.setAttribute('cy', this.currentPupilY.toFixed(2));

            // Smooth Viseme Mouth Path Interpolation (Lerp)
            this.currentViseme.openness += (this.targetViseme.openness - this.currentViseme.openness) * 0.25;
            this.currentViseme.width += (this.targetViseme.width - this.currentViseme.width) * 0.25;

            if (this.mouth) {
                const d = getVisemeSvgPath(this.currentViseme);
                this.mouth.setAttribute('d', d);
            }

            requestAnimationFrame(() => this.renderLoop());
        }
    }

    const mascot = new GhostyMascotController();

    // =======================================================================
    // 2. NAVIGATION VIEW SWITCHER
    // =======================================================================
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

        // View Refresh Hooks
        if (viewName === 'intelligence') loadMemoryAndGoals();
        if (viewName === 'workflows') loadWorkflows();
        if (viewName === 'channels') loadChannels();
        if (viewName === 'avatar') {
            mascot.setFaceMood('idle');
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

    const headerMiniMascot = document.getElementById('header-mini-mascot');
    if (headerMiniMascot) {
        headerMiniMascot.addEventListener('click', () => switchView('avatar'));
    }

    const btnExitAvatar = document.getElementById('btn-exit-avatar');
    if (btnExitAvatar) {
        btnExitAvatar.addEventListener('click', () => switchView('chat'));
    }

    // =======================================================================
    // 3. VOICE SPEECH SYNTHESIS & REPLAY ENGINE
    // =======================================================================
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

    function loadVoices() {
        if (!synth) return;
        const voices = synth.getVoices();
        if (voices.length === 0) return;

        // Choose preferred browser fallback voice without wiping high-end Neural options
        let preferredVoice = null;
        voices.forEach((v) => {
            if (!preferredVoice && (v.name.includes('Natural') || v.name.includes('Google') || v.name.includes('US') || v.lang.startsWith('en'))) {
                preferredVoice = v;
            }
        });
        selectedVoice = preferredVoice || voices[0];
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

    let currentAudioPlayer = null;

    function speakSpeech(text, onStart = null, onEnd = null) {
        if (!text) return;
        lastSpokenText = text;
        const clean = cleanTextForSpeech(text);
        if (!clean) return;

        // Stop any previous playing audio
        if (currentAudioPlayer) {
            currentAudioPlayer.pause();
            currentAudioPlayer.currentTime = 0;
            currentAudioPlayer = null;
        }
        if (synth) synth.cancel();

        const voiceSelect = document.getElementById('avatar-voice-select');
        const neuralVoice = voiceSelect ? voiceSelect.value : 'en-US-ChristopherNeural';

        // Option 1: Stream Edge-TTS High-Fidelity Microsoft Neural Audio
        const audioUrl = `/api/tts/synthesize?text=${encodeURIComponent(clean)}&voice=${encodeURIComponent(neuralVoice)}`;
        const player = new Audio(audioUrl);
        currentAudioPlayer = player;

        player.onplay = () => {
            mascot.setFaceMood('speaking');
            if (onStart) onStart();
        };

        player.onended = () => {
            mascot.setFaceMood('idle');
            currentAudioPlayer = null;
            if (onEnd) onEnd();
        };

        player.onerror = (e) => {
            console.warn('Neural audio stream error, falling back to WebSpeech:', e);
            currentAudioPlayer = null;
            fallbackWebSpeech(clean, onStart, onEnd);
        };

        player.play().catch(err => {
            console.warn('Audio auto-play policy blocked, fallback to WebSpeech:', err);
            fallbackWebSpeech(clean, onStart, onEnd);
        });
    }

    function fallbackWebSpeech(cleanText, onStart = null, onEnd = null) {
        if (!synth) {
            mascot.setFaceMood('idle');
            if (onEnd) onEnd();
            return;
        }
        try {
            const utterance = new SpeechSynthesisUtterance(cleanText);
            if (selectedVoice) utterance.voice = selectedVoice;
            utterance.rate = 1.05;

            utterance.onstart = () => {
                mascot.setFaceMood('speaking');
                if (onStart) onStart();
            };
            utterance.onend = () => {
                mascot.setFaceMood('idle');
                if (onEnd) onEnd();
            };
            utterance.onerror = () => {
                mascot.setFaceMood('idle');
                if (onEnd) onEnd();
            };
            synth.speak(utterance);
        } catch (err) {
            mascot.setFaceMood('idle');
            if (onEnd) onEnd();
        }
    }

    window.replaySpeech = function (text) {
        speakSpeech(text);
    };

    // =======================================================================
    // 4. CHAT STREAM & COMPOSER (With Markdown & Speaker Buttons)
    // =======================================================================
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

        if (!isUser && autoVoiceEnabled) {
            speakSpeech(text);
        }
    }

    async function handleSendMessage(inputOverride = null) {
        const text = inputOverride || chatInput.value.trim();
        if (!text) return;

        appendMessage('user', text);
        if (!inputOverride) chatInput.value = '';
        mascot.setFaceMood('thinking');

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
            mascot.setFaceMood('idle');
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

    // =======================================================================
    // 5. CONVERSATIONAL AVATAR VOICE CONTROLLER & AUTO-LOOP
    // =======================================================================
    const avatarLiveTranscript = document.getElementById('avatar-live-transcript');
    const btnAvatarSpeak = document.getElementById('btn-avatar-speak');
    const btnAvatarReplay = document.getElementById('btn-avatar-replay');
    const btnAvatarAutoLoop = document.getElementById('btn-avatar-auto-loop');
    const iconAutoLoop = document.getElementById('icon-auto-loop');

    let continuousAutoLoop = false;
    let isAvatarRecording = false;

    function updateAvatarSubtitles(text) {
        if (avatarLiveTranscript) {
            avatarLiveTranscript.innerText = `"${cleanTextForSpeech(text).substring(0, 240)}..."`;
        }
    }

    let recognition = null;
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
        const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
        recognition = new SpeechRec();
        recognition.continuous = false;
        recognition.interimResults = true;
        recognition.lang = 'en-US';

        recognition.onstart = () => {
            isAvatarRecording = true;
            mascot.setFaceMood('listening');
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
            mascot.setFaceMood('idle');
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
            mascot.setFaceMood('idle');
            return;
        }

        mascot.setFaceMood('thinking');
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

            speakSpeech(reply, () => {
                mascot.setFaceMood('speaking');
            }, () => {
                mascot.setFaceMood('idle');
                if (continuousAutoLoop) {
                    setTimeout(() => toggleAvatarListening(), 600);
                }
            });
        } catch (e) {
            mascot.setFaceMood('idle');
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
            } else {
                btnAvatarAutoLoop.classList.remove('bg-primary/20', 'border-primary', 'text-primary');
                iconAutoLoop.innerText = 'all_inclusive';
            }
        });
    }

    window.addEventListener('keydown', (e) => {
        if (e.code === 'Space' && document.getElementById('view-avatar') && !document.getElementById('view-avatar').classList.contains('hidden')) {
            if (document.activeElement !== chatInput && !isAvatarRecording) {
                e.preventDefault();
                toggleAvatarListening();
            }
        }
    });

    // =======================================================================
    // 6. MEMORY TREE & GOALS KANBAN LOADER
    // =======================================================================
    async function loadMemoryAndGoals() {
        try {
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

    // =======================================================================
    // 7. WORKFLOWS ENGINE (TINYFLOWS) LOADER
    // =======================================================================
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

    // =======================================================================
    // 8. MULTI-CHANNEL HUB LOADER
    // =======================================================================
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

    // Default start view
    switchView('chat');
});
