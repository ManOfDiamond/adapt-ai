let currentHost = window.location.hostname || "127.0.0.1";
const API_BASE = "http://" + currentHost + ":8000/api";

const STORAGE_KEY = "adapt_ai_sessions";
let chatSessions = []; 
let currentSessionId = null; 
let abortController = null; 
let telemetryInterval;
let pendingAttachmentText = null; 
let pendingAttachmentImageBase64 = null;
let telemetryHistoryChart = null; 

const generateId = () => Math.random().toString(36).substr(2, 9);

window.addEventListener('DOMContentLoaded', () => {
    initTelemetryLiveGraphChart(); 
    
    ["num_ctx"].forEach(param => {
        const el = document.getElementById(`slider-${param}`);
        if(el) el.oninput = (e) => { document.getElementById(`label-${param}`).innerText = e.target.value; };
    });

    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
        chatSessions = JSON.parse(saved);
        chatSessions.sort((a, b) => b.updatedAt - a.updatedAt);
    }
    renderSidebar();
});

function initTelemetryLiveGraphChart() {
    const ctx = document.getElementById('telemetryLiveGraphCanvas').getContext('2d');
    telemetryHistoryChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: Array(15).fill(''),
            datasets: [
                { label: 'RAM', data: Array(15).fill(0), borderColor: '#94a3b8', borderWidth: 1.5, pointRadius: 0, tension: 0.3 },
                { label: 'VRAM', data: Array(15).fill(0), borderColor: '#22d3ee', borderWidth: 1.5, pointRadius: 0, tension: 0.3 }
            ]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: { x: { display: false }, y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#475569', font: { size: 9 } } } }
        }
    });
}

function saveSessions() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(chatSessions));
    renderSidebar();
    renderChatHistoryUI(); 
}

function createNewWorkspace() {
    const newSession = {
        id: generateId(),
        title: "New Workspace",
        messages: [{ role: "system", content: "You are a helpful AI assistant." }],
        updatedAt: Date.now()
    };
    chatSessions.unshift(newSession); 
    switchWorkspace(newSession.id);
}

function switchWorkspace(id) {
    if(abortController) abortController.abort(); 
    currentSessionId = id;
    saveSessions();
}

function deleteWorkspace(id, event) {
    event.stopPropagation(); 
    chatSessions = chatSessions.filter(s => s.id !== id);
    if (currentSessionId === id) {
        currentSessionId = chatSessions.length > 0 ? chatSessions[0].id : null;
        if (!currentSessionId) createNewWorkspace();
        else switchWorkspace(currentSessionId);
    } else {
        saveSessions();
    }
}

window.switchWorkspace = switchWorkspace;
window.deleteWorkspace = deleteWorkspace;

function renderSidebar() {
    const listContainer = document.getElementById('sidebarChatList');
    listContainer.innerHTML = "";
    
    chatSessions.forEach(session => {
        const isActive = session.id === currentSessionId;
        const activeClasses = isActive ? "bg-slate-800 border-cyan-500/50 text-cyan-300" : "border-transparent hover:bg-slate-800/50 text-slate-300 hover:text-slate-100";
        
        listContainer.insertAdjacentHTML('beforeend', `
        <div onclick="switchWorkspace('${session.id}')" class="group flex items-center justify-between p-3 rounded-lg border ${activeClasses} cursor-pointer transition-all">
            <div class="truncate text-sm flex-1 pr-2">${session.title}</div>
            <button onclick="deleteWorkspace('${session.id}', event)" class="opacity-0 group-hover:opacity-100 text-slate-500 hover:text-red-400 transition-opacity">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>
            </button>
        </div>
        `);
    });
}

document.getElementById('newWorkspaceBtn').addEventListener('click', createNewWorkspace);

function log(message, colorClass = 'text-slate-400') {
    const logsContainer = document.getElementById('terminalLogs');
    logsContainer.insertAdjacentHTML('beforeend', `<div><span class="text-slate-600 mr-2 opacity-50">></span><span class="${colorClass}">${message}</span></div>`);
    logsContainer.scrollTop = logsContainer.scrollHeight;
}

document.getElementById('scanBtn').addEventListener('click', async () => {
    document.getElementById('terminalLogs').innerHTML = '';
    log("Initializing hardware telemetry...");
    try {
        const res = await fetch(API_BASE + "/benchmark");
        const data = await res.json();
        if(data.safe) {
            document.getElementById('resultsCard').classList.remove('opacity-30', 'pointer-events-none');
            document.getElementById('sysRamLabel').innerText = `${data.memory.available_ram_gb} GB / ${data.memory.total_ram_gb} GB`;
            
            if(data.memory.has_gpu) {
                document.getElementById('vramContainer').classList.remove('hidden');
                document.getElementById('liveVramContainer').classList.remove('hidden');
                document.getElementById('vramLabel').innerText = `${data.memory.gpu_free_vram_gb} GB / ${data.memory.gpu_total_vram_gb} GB`;
            }
            
            const scoreContainer = document.getElementById('scoreContainer');
            scoreContainer.classList.remove('hidden');
            document.getElementById('scoreNumber').innerText = data.compatibility_score + "%";
            setTimeout(() => {
                const circle = document.getElementById('scoreCircle');
                circle.style.strokeDashoffset = 100 - data.compatibility_score;
            }, 100);

            const dropdown = document.getElementById('modelDropdown');
            const chatDropdown = document.getElementById('chatModelDropdown');
            dropdown.innerHTML = ''; chatDropdown.innerHTML = '';
            
            data.catalog.forEach(m => {
                const opt1 = document.createElement('option');
                const opt2 = document.createElement('option');
                opt1.value = opt2.value = m.id; 
                opt1.innerText = m.name + (m.id === data.recommendation ? ' (Rec)' : '');
                opt2.innerText = m.name;
                if(m.id === data.recommendation) { opt1.selected = true; opt2.selected = true; }
                dropdown.appendChild(opt1); chatDropdown.appendChild(opt2);
            });

            dropdown.addEventListener('change', (e) => chatDropdown.value = e.target.value);
            chatDropdown.addEventListener('change', (e) => dropdown.value = e.target.value);
        }
    } catch(e) { log("Error connecting to backend.", "text-red-400"); }
});

document.getElementById('loadChatBtn').onclick = () => {
    document.getElementById('profilerSection').classList.add('hidden');
    document.getElementById('chatSection').classList.remove('hidden');
    document.getElementById('chatSection').classList.add('flex');
    
    document.getElementById('appSidebar').classList.remove('hidden');
    document.getElementById('appSidebar').classList.add('flex');
    
    document.getElementById('appRightSidebar').classList.remove('hidden');
    document.getElementById('appRightSidebar').classList.add('flex');

    if (!currentSessionId) {
        if (chatSessions.length > 0) switchWorkspace(chatSessions[0].id);
        else createNewWorkspace();
    }
    
    telemetryInterval = setInterval(async () => {
        try {
            const res = await fetch(API_BASE + "/metrics");
            const mem = await res.json();
            document.getElementById('liveRam').innerText = mem.available_ram_gb + " GB";
            
            let vramUsed = 0;
            if(mem.has_gpu) {
                document.getElementById('liveVram').innerText = mem.gpu_free_vram_gb + " GB";
                vramUsed = mem.gpu_used_vram_gb;
            }

            if(telemetryHistoryChart) {
                telemetryHistoryChart.data.datasets[0].data.push(mem.used_ram_gb);
                telemetryHistoryChart.data.datasets[0].data.shift();
                telemetryHistoryChart.data.datasets[1].data.push(vramUsed);
                telemetryHistoryChart.data.datasets[1].data.shift();
                telemetryHistoryChart.update();
            }
        } catch(e) {}
    }, 2500);
};

window.editMessage = function(index) {
    const activeSession = chatSessions.find(s => s.id === currentSessionId);
    const originalText = activeSession.messages[index].content;
    const container = document.getElementById(`msg-${index}-container`);

    container.innerHTML = `
        <textarea id="edit-input-${index}" class="w-full bg-slate-100 text-slate-900 p-3 rounded-lg border focus:outline-cyan-500 min-h-[100px] shadow-inner font-mono text-xs">${originalText}</textarea>
        <div class="flex justify-end gap-3 mt-3">
        <button onclick="saveSessions()" class="text-xs text-slate-500 hover:text-slate-700 font-bold transition-colors">Cancel</button>
        <button onclick="submitEdit(${index})" class="text-xs bg-cyan-600 text-white px-4 py-2 rounded-lg hover:bg-cyan-500 font-bold shadow-md transition-colors">Save & Send</button>
        </div>
    `;
}

window.submitEdit = async function(index) {
    const activeSession = chatSessions.find(s => s.id === currentSessionId);
    const newText = document.getElementById(`edit-input-${index}`).value.trim();
    if(!newText) return;

    activeSession.messages[index].content = newText;
    activeSession.messages = activeSession.messages.slice(0, index + 1);
    
    saveSessions(); 
    await generateResponse(activeSession);
}

function attachCodeSandboxActionButtons(containerId) {
    const bubble = document.getElementById(containerId);
    if (!bubble) return;
    const preBlocks = bubble.querySelectorAll('pre');
    
    preBlocks.forEach((pre) => {
        if (pre.querySelector('.sandbox-mount')) return; 
        const codeElement = pre.querySelector('code');
        const pureCodeString = codeElement ? codeElement.innerText : pre.innerText;

        const widget = document.createElement('div');
        widget.className = "sandbox-mount mt-2 flex flex-col border-t border-white/10 pt-2";
        widget.innerHTML = `
            <button type="button" class="run-code-btn self-start bg-emerald-400/10 hover:bg-emerald-400/20 text-emerald-400 text-[10px] font-mono font-semibold px-2.5 py-1 rounded border border-emerald-400/20 active:scale-95 transition-all">▶ Execute Python</button>
            <div class="console-output hidden mt-2 p-2 bg-slate-950 border border-white/5 rounded-lg font-mono text-[11px] text-emerald-400 whitespace-pre-wrap shadow-inner"></div>
        `;

        widget.querySelector('.run-code-btn').onclick = async (e) => {
            const btn = e.target; const consoleBox = widget.querySelector('.console-output');
            btn.innerText = "⏳ Executing..."; consoleBox.classList.remove('hidden'); consoleBox.innerText = "Initializing runtime space...";
            try {
                const res = await fetch(`${API_BASE}/execute`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ code: pureCodeString }) });
                const runResult = await res.json(); 
                consoleBox.innerText = runResult.output;
                consoleBox.className = `console-output mt-2 p-2 bg-slate-950 border border-white/5 rounded-lg font-mono text-[11px] whitespace-pre-wrap ${runResult.success ? 'text-emerald-400' : 'text-rose-400'}`;
            } catch { consoleBox.innerText = "Runtime pipeline handshake dropped."; } finally { btn.innerText = "▶ Execute Python"; }
        };
        pre.appendChild(widget);
    });
}

function renderChatHistoryUI() {
    const chatHistory = document.getElementById('chatHistory');
    chatHistory.innerHTML = ""; 
    
    const activeSession = chatSessions.find(s => s.id === currentSessionId);
    if (!activeSession) return;

    if (activeSession.messages.length <= 1) {
        chatHistory.insertAdjacentHTML('beforeend', `
            <div class="flex items-start gap-4">
            <div class="w-8 h-8 rounded-full bg-gradient-to-br from-cyan-400 to-emerald-500 flex items-center justify-center text-white shrink-0">V</div>
            <div class="bg-slate-800/80 p-4 rounded-2xl rounded-tl-sm text-sm text-slate-200 border border-white/5">Hardware guardrails active. Ready for new queries.</div>
            </div>
        `);
        return;
    }

    activeSession.messages.forEach((msg, index) => {
        if (msg.role === 'system') return;
        
        let displayContent = msg.content;
        if(msg.images && msg.images.length > 0) {
            displayContent = `<div class="mb-2 text-xs text-emerald-400 border border-emerald-500/30 bg-emerald-900/20 px-2 py-1 rounded inline-block">📸 Image Attached</div><br>${displayContent}`;
        }

        const bubbleId = `bubble-${currentSessionId}-${index}`;

        if (msg.role === 'user') {
            chatHistory.insertAdjacentHTML('beforeend', `
                <div class="flex items-start gap-4 justify-end w-full group">
                <button onclick="editMessage(${index})" class="opacity-0 group-hover:opacity-100 text-slate-500 hover:text-cyan-400 mt-2 p-2 transition-opacity" title="Edit Message">✏️</button>
                <div id="msg-${index}-container" class="bg-white text-slate-900 p-4 rounded-2xl rounded-tr-sm text-sm font-medium max-w-[85%] whitespace-pre-wrap shadow-md">${displayContent}</div>
                </div>
            `);
        } else {
            chatHistory.insertAdjacentHTML('beforeend', `
                <div class="flex items-start gap-4 w-full">
                <div class="w-8 h-8 rounded-full bg-gradient-to-br from-cyan-400 to-emerald-500 flex items-center justify-center text-white shrink-0">V</div>
                <div id="${bubbleId}" class="bg-slate-800/80 p-4 rounded-2xl rounded-tl-sm text-sm text-slate-200 border border-white/5 prose max-w-[85%] overflow-x-auto">${marked.parse(msg.content)}</div>
                </div>
            `);
            attachCodeSandboxActionButtons(bubbleId);
        }
    });
    chatHistory.scrollTop = chatHistory.scrollHeight;
}

const fileUpload = document.getElementById('fileUpload');
const attachmentPreview = document.getElementById('attachmentPreview');
const attachmentName = document.getElementById('attachmentName');

document.getElementById('attachBtn').onclick = () => fileUpload.click();
document.getElementById('removeAttachmentBtn').onclick = () => {
    fileUpload.value = ""; pendingAttachmentText = null; pendingAttachmentImageBase64 = null; attachmentPreview.classList.add('hidden');
};

fileUpload.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (!file) return;
    attachmentName.innerText = `📎 ${file.name}`;
    attachmentPreview.classList.remove('hidden');
    const reader = new FileReader();
    
    if (file.type.startsWith('image/')) {
        reader.onload = (event) => {
            pendingAttachmentImageBase64 = event.target.result.split(',')[1];
            pendingAttachmentText = null; 
        };
        reader.readAsDataURL(file);
    } else {
        reader.onload = (event) => {
            pendingAttachmentText = `\n\n--- [FILE ATTACHMENT: ${file.name}] ---\n${event.target.result}\n---------------------------\n`;
            pendingAttachmentImageBase64 = null;
        };
        reader.readAsText(file);
    }
});

document.getElementById('stopBtn').addEventListener('click', () => {
    if(abortController) { abortController.abort(); abortController = null; }
});

async function generateResponse(activeSession) {
    const chatHistory = document.getElementById('chatHistory');
    const selectedModelId = document.getElementById('chatModelDropdown').value;

    document.getElementById('sendBtn').classList.add('hidden');
    document.getElementById('stopBtn').classList.remove('hidden');
    document.getElementById('chatInput').disabled = true;

    const aiResponseId = "ai-" + Date.now();
    chatHistory.insertAdjacentHTML('beforeend', `
        <div class="flex items-start gap-4 w-full">
        <div class="w-8 h-8 rounded-full bg-gradient-to-br from-cyan-400 to-emerald-500 flex items-center justify-center text-white shrink-0 shadow-lg shadow-cyan-500/20">V</div>
        <div id="${aiResponseId}" class="bg-slate-800/80 p-4 rounded-2xl rounded-tl-sm text-sm text-slate-200 border border-white/5 w-full max-w-[85%] prose prose-invert">
            <span class="animate-pulse">Initializing request...</span>
        </div>
        </div>
    `);
    chatHistory.scrollTop = chatHistory.scrollHeight;
    const aiBubble = document.getElementById(aiResponseId);

    abortController = new AbortController();

    try {
        const response = await fetch(API_BASE + "/chat", {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                model: selectedModelId, 
                messages: activeSession.messages,
                options: {
                    num_ctx: parseInt(document.getElementById('slider-num_ctx').value)
                }
            }),
            signal: abortController.signal
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        
        let currentReply = "";
        let buffer = ""; 

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop(); 

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const jsonData = JSON.parse(line.slice(6));
                        
                        // Clear the "Initializing request..." text once real data arrives
                        if (aiBubble.querySelector('.animate-pulse')) {
                            aiBubble.innerHTML = ''; 
                        }

                        currentReply += (jsonData.content || '');
                        aiBubble.innerHTML = marked.parse(currentReply);
                        chatHistory.scrollTop = chatHistory.scrollHeight;
                    } catch(e) {
                        console.warn("Skipping partial chunk buffer");
                    }
                }
            }
        }

        activeSession.messages.push({ role: "assistant", content: currentReply });
        activeSession.updatedAt = Date.now();
        saveSessions();
        attachCodeSandboxActionButtons(aiResponseId);
    } catch (err) {
        if (err.name === 'AbortError') {
            aiBubble.innerHTML += "<br><br><em class='text-amber-500'>[Generation safely interrupted.]</em>";
            activeSession.messages.push({ role: "assistant", content: aiBubble.innerText });
            saveSessions();
        } else {
            aiBubble.innerHTML += "<div class='text-red-400 mt-2'>[Connection Error] Ensure backend is running.</div>";
        }
    } finally {
        document.getElementById('chatInput').disabled = false;
        document.getElementById('chatInput').focus();
        document.getElementById('sendBtn').classList.remove('hidden');
        document.getElementById('stopBtn').classList.add('hidden');
    }
}

document.getElementById('chatForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const chatInput = document.getElementById('chatInput');
    let promptText = chatInput.value.trim();
    const rawUserText = promptText; 
    
    if (pendingAttachmentText) promptText += pendingAttachmentText;
    if (!promptText && !pendingAttachmentImageBase64) return;

    const activeSession = chatSessions.find(s => s.id === currentSessionId);

    if (activeSession.title === "New Workspace") {
        let newTitle = rawUserText || "Image Analysis";
        if (newTitle.length > 25) newTitle = newTitle.substring(0, 25) + '...';
        activeSession.title = newTitle;
    }

    const newMessage = { role: "user", content: promptText };
    if (pendingAttachmentImageBase64) newMessage.images = [pendingAttachmentImageBase64];

    activeSession.messages.push(newMessage);
    activeSession.updatedAt = Date.now();
    
    saveSessions(); 
    
    chatInput.value = '';
    document.getElementById('removeAttachmentBtn').click(); 
    
    await generateResponse(activeSession);
});