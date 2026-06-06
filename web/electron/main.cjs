const { app, BrowserWindow, ipcMain, shell } = require('electron');
const { execFile } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');

function projectRoot() {
  return path.resolve(__dirname, '..', '..');
}

function pythonExecutable() {
  const candidates = [
    process.env.PYTHON,
    path.join(projectRoot(), '.venv', 'Scripts', 'python.exe'),
    'python',
  ].filter(Boolean);

  for (const candidate of candidates) {
    if (candidate !== 'python' && fs.existsSync(candidate)) {
      return candidate;
    }
  }

  return 'python';
}

function runPython(args) {
  return new Promise((resolve, reject) => {
    execFile(
      pythonExecutable(),
      ['-m', 'optimizer_pc.cli', ...args],
      {
        cwd: projectRoot(),
        windowsHide: true,
        maxBuffer: 10 * 1024 * 1024,
      },
      (error, stdout, stderr) => {
        if (error) {
          reject(new Error(stderr || error.message));
          return;
        }

        try {
          resolve(JSON.parse(stdout || '{}'));
        } catch (parseError) {
          reject(new Error(`Falha ao interpretar resposta do Python: ${parseError.message}`));
        }
      },
    );
  });
}

function createWindow() {
  const win = new BrowserWindow({
    width: 1400,
    height: 940,
    minWidth: 1100,
    minHeight: 760,
    backgroundColor: '#050b14',
    title: 'Otimizer PC',
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  });

  const indexPath = path.join(projectRoot(), 'web', 'dist', 'index.html');
  if (fs.existsSync(indexPath)) {
    win.loadFile(indexPath);
  } else {
    win.loadURL(
      'data:text/html;charset=utf-8,<h1 style="font-family:sans-serif;padding:24px;color:#fff;background:#050b14">Execute <code>npm run build</code> em <code>web/</code> antes de abrir o app.</h1>',
    );
  }

  if (process.env.NODE_ENV !== 'production') {
    const distDir = path.join(projectRoot(), 'web', 'dist');
    let reloadTimer = null;
    try {
      fs.watch(distDir, { recursive: true }, () => {
        clearTimeout(reloadTimer);
        reloadTimer = setTimeout(() => {
          if (!win.isDestroyed()) {
            win.reload();
          }
        }, 150);
      });
    } catch (error) {
      // Falha silenciosa: em alguns ambientes o watch recursivo pode não estar disponível.
    }
  }
}

app.whenReady().then(() => {
  ipcMain.handle('system:snapshot', async () => runPython(['snapshot']));
  ipcMain.handle('system:processes', async (_event, limit = 8) => runPython(['processes', '--limit', String(limit)]));
  ipcMain.handle('system:network', async (_event, limit = 40) => runPython(['network', '--limit', String(limit)]));
  ipcMain.handle('system:files', async (_event, options = {}) => {
    const limit = String(options.limit ?? 40);
    const recentDays = String(options.recentDays ?? 7);
    const args = ['files', '--limit', limit, '--recent-days', recentDays];
    if (options.source) {
      args.push('--source', String(options.source));
    }
    return runPython(args);
  });
  ipcMain.handle('system:power', async () => runPython(['power']));
  ipcMain.handle('system:cleanup', async (_event, confirm = false) => {
    if (!confirm) {
      throw new Error('Confirmação necessária para limpar temporários.');
    }
    return runPython(['cleanup', '--confirm']);
  });
  ipcMain.handle('app:openExternal', async (_event, url) => shell.openExternal(url));

  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});
