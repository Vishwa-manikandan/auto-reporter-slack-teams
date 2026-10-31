const { ipcRenderer } = require('electron');

let logs = [];

// Tab switching
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        
        btn.classList.add('active');
        document.getElementById(btn.dataset.tab).classList.add('active');
    });
});

// Load settings
async function loadSettings() {
    const settings = await ipcRenderer.invoke('get-settings');
    document.getElementById('slackToken').value = settings.slackToken;
    document.getElementById('channelId').value = settings.channelId;
    document.getElementById('channelName').value = settings.channelName;
    document.getElementById('scheduleTime').value = settings.scheduleTime;
    document.getElementById('scheduleEnabled').checked = settings.scheduleEnabled;
}

loadSettings();

// Save settings
document.getElementById('saveSettingsBtn').addEventListener('click', async () => {
    const settings = {
        slackToken: document.getElementById('slackToken').value,
        channelId: document.getElementById('channelId').value,
        channelName: document.getElementById('channelName').value,
        scheduleTime: document.getElementById('scheduleTime').value,
        scheduleEnabled: document.getElementById('scheduleEnabled').checked
    };
    
    const result = await ipcRenderer.invoke('save-settings', settings);
    const status = document.getElementById('settingsStatus');
    
    if (result.success) {
        status.textContent = 'Settings saved successfully!';
        status.className = 'status success';
        addLog('Settings saved');
    }
    
    setTimeout(() => {
        status.className = 'status';
    }, 3000);
});

// Generate report
document.getElementById('generateBtn').addEventListener('click', async () => {
    const btn = document.getElementById('generateBtn');
    const status = document.getElementById('reportStatus');
    const preview = document.getElementById('reportPreview');
    const lastRun = document.getElementById('lastRun');
    
    btn.disabled = true;
    btn.textContent = 'Generating...';
    status.className = 'status';
    
    addLog('Generating report...');
    
    const result = await ipcRenderer.invoke('generate-report');
    
    if (result.success) {
        status.textContent = 'Report generated successfully!';
        status.className = 'status success';
        preview.textContent = result.output;
        lastRun.innerHTML = `<p><strong>Last Run:</strong> ${new Date().toLocaleString()}</p>`;
        addLog('Report generated successfully');
    } else {
        status.textContent = 'Error generating report';
        status.className = 'status error';
        preview.textContent = result.error;
        addLog(`Error: ${result.error}`);
    }
    
    btn.disabled = false;
    btn.textContent = 'Generate Report Now';
    
    setTimeout(() => {
        status.className = 'status';
    }, 5000);
});

// Scheduled report listener
ipcRenderer.on('scheduled-report', (event, result) => {
    addLog('Scheduled report generated');
    if (result.success) {
        document.getElementById('reportPreview').textContent = result.output;
        document.getElementById('lastRun').innerHTML = `<p><strong>Last Run (Scheduled):</strong> ${new Date().toLocaleString()}</p>`;
    }
});

// Logs
function addLog(message) {
    const timestamp = new Date().toLocaleTimeString();
    logs.unshift(`[${timestamp}] ${message}`);
    updateLogsDisplay();
}

function updateLogsDisplay() {
    const logsList = document.getElementById('logsList');
    if (logs.length === 0) {
        logsList.innerHTML = '<p class="muted">No logs yet</p>';
        return;
    }
    logsList.innerHTML = logs.map(log => `<p>${log}</p>`).join('');
}

document.getElementById('clearLogsBtn').addEventListener('click', () => {
    logs = [];
    updateLogsDisplay();
    addLog('Logs cleared');
});
