/**
 * JARVIS General Purpose AI Super-Assistant — Interactive UI Controller
 * Integrates OpenHuman-Inspired Memory Tree, Workflows (Tinyflows), Multi-Channel Hub, 
 * Voice PTT, Mascot Reactions, and PCB Hardware Suites.
 */

document.addEventListener('DOMContentLoaded', () => {
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
        if (viewName === 'tools') loadToolsCatalog();
    }

    navButtons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            switchView(btn.getAttribute('data-view'));
        });
    });

    // -----------------------------------------------------------------------
    // 2. Chat Stream & Message Handling
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
                <div class="mt-2 p-2.5 rounded-lg bg-surface-card border border-primary/30 font-mono text-xs space-y-1">
                    <div class="flex items-center justify-between text-primary">
                        <span class="flex items-center gap-1 font-bold">
                            <span class="material-symbols-outlined text-xs">build</span>
                            ${toolMeta.tool_name || 'Tool Executed'}
                        </span>
                        <span class="text-[10px] text-success">SUCCESS (0.12s)</span>
                    </div>
                    <div class="text-[11px] text-on-surface-variant break-all">${toolMeta.summary || ''}</div>
                </div>
            `;
        }

        const bubble = `
            <div class="space-y-1 max-w-2xl">
                <div class="px-4 py-3 rounded-2xl text-sm leading-relaxed ${
                    isUser
                        ? 'bg-primary/20 text-on-surface border border-primary/30 rounded-tr-none'
                        : 'glass-panel text-on-surface border border-surface-border rounded-tl-none'
                }">
                    ${text.replace(/\n/g, '<br/>')}
                    ${toolHtml}
                </div>
                <div class="text-[10px] font-mono text-on-surface-variant px-1 ${isUser ? 'text-right' : 'text-left'}">
                    ${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </div>
            </div>
        `;

        msgDiv.innerHTML = isUser ? bubble + avatar : avatar + bubble;
        chatStream.appendChild(msgDiv);
        chatStream.scrollTop = chatStream.scrollHeight;
    }

    async function handleSendMessage() {
        const text = chatInput.value.trim();
        if (!text) return;

        appendMessage('user', text);
        chatInput.value = '';
        setMascotMood('thinking');

        try {
            const resp = await fetch('/api/agent/command', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ command: text })
            });
            const data = await resp.json();
            setMascotMood('success');

            const summary = data.summary || (data.data && data.data.result) || JSON.stringify(data);
            appendMessage('assistant', summary, {
                tool_name: data.data?.tool_slug || 'Jarvis Reasoning Core',
                summary: data.data?.details || data.summary
            });
        } catch (e) {
            setMascotMood('alert');
            appendMessage('assistant', `⚠️ Execution Error: ${e.message}`);
        }
    }

    btnSend.addEventListener('click', handleSendMessage);
    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSendMessage();
        }
    });

    document.querySelectorAll('.quick-prompt-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            chatInput.value = btn.innerText.replace(/^[^\"]*\"|\"[^\"]*$/g, '');
            handleSendMessage();
        });
    });

    // -----------------------------------------------------------------------
    // 3. Mascot Mood & Audio Visualizer Reaction
    // -----------------------------------------------------------------------
    const mascotBadge = document.getElementById('mascot-badge');
    function setMascotMood(mood) {
        if (!mascotBadge) return;
        mascotBadge.classList.remove('glow-cyan', 'ring-2', 'ring-warning', 'ring-error', 'ring-success');
        if (mood === 'thinking') {
            mascotBadge.classList.add('glow-cyan', 'animate-spin');
        } else if (mood === 'listening') {
            mascotBadge.classList.add('ring-2', 'ring-primary', 'animate-pulse');
        } else if (mood === 'success') {
            mascotBadge.classList.remove('animate-spin');
            mascotBadge.classList.add('ring-2', 'ring-success');
            setTimeout(() => mascotBadge.classList.remove('ring-2', 'ring-success'), 2000);
        } else if (mood === 'alert') {
            mascotBadge.classList.remove('animate-spin');
            mascotBadge.classList.add('ring-2', 'ring-error');
        }
    }

    // -----------------------------------------------------------------------
    // 4. Voice PTT (Push-To-Talk)
    // -----------------------------------------------------------------------
    const pttBtn = document.getElementById('header-ptt-btn');
    const pttLabel = document.getElementById('header-ptt-label');
    const pttIcon = document.getElementById('header-mic-icon');
    let isListening = false;
    let recognition = null;

    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = 'en-US';

        recognition.onstart = () => {
            isListening = true;
            pttLabel.innerText = 'LISTENING...';
            pttBtn.classList.add('bg-error/30', 'text-error', 'border-error');
            setMascotMood('listening');
        };

        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            chatInput.value = transcript;
            handleSendMessage();
        };

        recognition.onend = () => {
            isListening = false;
            pttLabel.innerText = 'VOICE PTT';
            pttBtn.classList.remove('bg-error/30', 'text-error', 'border-error');
            setMascotMood('ready');
        };

        pttBtn.addEventListener('click', () => {
            if (!isListening) {
                recognition.start();
            } else {
                recognition.stop();
            }
        });
    }

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
            const logContainer = document.getElementById('workflow-run-logs');
            if (logContainer) {
                const logEntry = document.createElement('div');
                logEntry.className = 'p-2 bg-surface-card rounded border border-success/40 text-success text-xs font-mono';
                logEntry.innerText = `[${new Date().toLocaleTimeString()}] Executed Workflow '${data.data?.workflow_name}': Run #${data.data?.run_id} completed successfully.`;
                logContainer.prepend(logEntry);
            }
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

    // -----------------------------------------------------------------------
    // 8. 80+ Tools Surface Catalog
    // -----------------------------------------------------------------------
    function loadToolsCatalog() {
        const tools = [
            { category: 'Memory & Intelligence', name: 'memory_tree_store', desc: 'Stores scored hierarchical memory node in SQLite & Obsidian' },
            { category: 'Memory & Intelligence', name: 'goals_kanban_upsert', desc: 'Updates Goals & Tasks Kanban card' },
            { category: 'Automation & Flows', name: 'workflow_execute', desc: 'Runs trigger-driven Tinyflows multi-step graph' },
            { category: 'Communications', name: 'channel_send_message', desc: 'Dispatches message to Telegram, Discord, Slack, WhatsApp' },
            { category: 'Optimization', name: 'tokenjuice_compress', desc: 'Compresses tool outputs up to 80% to save LLM tokens' },
            { category: 'PCB & Hardware', name: 'analyze_kicad_file', desc: 'Full AST netlist, power tree, and DRC clearance parser' },
            { category: 'PCB & Hardware', name: 'generate_3d_part_from_image_or_spec', desc: 'Procedural 3D OBJ & Three.js electronic model generator' },
            { category: 'PCB & Hardware', name: 'calculate_thermal_loss', desc: 'Joule heating and trace temperature rise simulator' },
            { category: 'Web & Research', name: 'browse_web_page', desc: 'Crawl4AI & Scrapling dynamic DOM crawler' },
            { category: 'Composio Cloud', name: 'gmail_send_email', desc: 'Sends email via authenticated Gmail connection' },
            { category: 'Composio Cloud', name: 'sheets_append_row', desc: 'Appends rows into live Google Sheets database' },
            { category: 'Composio Cloud', name: 'notion_create_page', desc: 'Creates pages and task boards in Notion workspace' }
        ];

        const grid = document.getElementById('tools-catalog-grid');
        if (grid) {
            grid.innerHTML = tools.map(t => `
                <div class="glass-panel p-3 rounded-xl border border-surface-border space-y-1.5 hover:border-primary/40 transition-all">
                    <span class="text-[9px] px-1.5 py-0.5 rounded bg-primary/10 text-primary font-bold uppercase">${t.category}</span>
                    <h4 class="font-bold text-xs text-on-surface font-mono">${t.name}</h4>
                    <p class="text-[10px] text-on-surface-variant font-sans">${t.desc}</p>
                </div>
            `).join('');
        }
    }

    // Initial Load
    switchView('chat');
});
