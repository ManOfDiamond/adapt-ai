let currentHost = window.location.hostname || "127.0.0.1";
const API_BASE = "http://" + currentHost + ":8000/api";

let telemetryInterval;
let telemetryHistoryChart = null;

window.addEventListener('DOMContentLoaded', () => {
    initTelemetryLiveGraphChart();

    ["num_ctx"].forEach(param => {
        const el = document.getElementById(`slider-${param}`);
        if(el) el.oninput = (e) => { document.getElementById(`label-${param}`).innerText = e.target.value; };
    });
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

    document.getElementById('chatHistory').innerHTML = `
        <div class="flex items-start gap-4">
        <div class="w-8 h-8 rounded-full bg-gradient-to-br from-cyan-400 to-emerald-500 flex items-center justify-center text-white shrink-0">V</div>
        <div class="bg-slate-800/80 p-4 rounded-2xl rounded-tl-sm text-sm text-slate-200 border border-white/5">Chat workspace coming soon — hardware profiling is live.</div>
        </div>
    `;

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
