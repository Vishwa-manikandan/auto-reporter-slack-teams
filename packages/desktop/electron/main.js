const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const Store = require('electron-store');
const cron = require('node-cron');

const store = new Store();
let mainWindow;
let scheduledJob = null;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 900,
    height: 700,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false
    }
  });

  mainWindow.loadFile(path.join(__dirname, '../renderer/index.html'));
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});

// IPC handlers
ipcMain.handle('get-settings', () => {
  return {
    slackToken: store.get('slackToken', ''),
    channelId: store.get('channelId', ''),
    channelName: store.get('channelName', 'channel'),
    scheduleTime: store.get('scheduleTime', '08:00'),
    scheduleEnabled: store.get('scheduleEnabled', false)
  };
});

ipcMain.handle('save-settings', (event, settings) => {
  store.set('slackToken', settings.slackToken);
  store.set('channelId', settings.channelId);
  store.set('channelName', settings.channelName);
  store.set('scheduleTime', settings.scheduleTime);
  store.set('scheduleEnabled', settings.scheduleEnabled);
  
  setupSchedule();
  return { success: true };
});

ipcMain.handle('generate-report', async () => {
  return new Promise((resolve, reject) => {
    const settings = store.store;
    const python = spawn('python', ['-m', 'autoreporter'], {
      env: {
        ...process.env,
        SLACK_BOT_TOKEN: settings.slackToken,
        SLACK_CHANNEL_ID: settings.channelId
      },
      cwd: path.join(__dirname, '..')
    });

    let output = '';
    let error = '';

    python.stdout.on('data', (data) => {
      output += data.toString();
    });

    python.stderr.on('data', (data) => {
      error += data.toString();
    });

    python.on('close', (code) => {
      if (code === 0) {
        resolve({ success: true, output });
      } else {
        resolve({ success: false, error: error || output });
      }
    });
  });
});

function setupSchedule() {
  if (scheduledJob) {
    scheduledJob.stop();
  }

  const scheduleEnabled = store.get('scheduleEnabled', false);
  if (!scheduleEnabled) return;

  const scheduleTime = store.get('scheduleTime', '08:00');
  const [hour, minute] = scheduleTime.split(':');
  
  // Run daily at specified time
  scheduledJob = cron.schedule(`${minute} ${hour} * * *`, async () => {
    const result = await ipcMain.handle('generate-report');
    if (mainWindow) {
      mainWindow.webContents.send('scheduled-report', result);
    }
  });
}
