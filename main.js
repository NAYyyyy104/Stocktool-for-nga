const { app, BrowserWindow, ipcMain } = require("electron");
const { spawn } = require("child_process");
const fs = require("fs");
const path = require("path");

let backendProcess = null;

function dataFilePath() {
  return path.join(__dirname, "cgp-data.json");
}

function backupFilePath() {
  return path.join(__dirname, "cgp-data.backup.json");
}

function legacyDataFilePath() {
  return path.join(app.getPath("userData"), "cgp-data.json");
}

function legacyBackupFilePath() {
  return path.join(app.getPath("userData"), "cgp-data.backup.json");
}

function normalizeRows(data) {
  if (!Array.isArray(data)) return null;
  return data;
}

function tryParseJson(raw) {
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function readRowsFromDisk() {
  const file = dataFilePath();
  const backup = backupFilePath();
  const legacyFile = legacyDataFilePath();
  const legacyBackup = legacyBackupFilePath();

  if (fs.existsSync(file)) {
    const parsed = tryParseJson(fs.readFileSync(file, "utf8"));
    const rows = normalizeRows(parsed);
    if (rows) return rows;
  }

  if (fs.existsSync(backup)) {
    const parsed = tryParseJson(fs.readFileSync(backup, "utf8"));
    const rows = normalizeRows(parsed);
    if (rows) return rows;
  }

  if (fs.existsSync(legacyFile)) {
    const parsed = tryParseJson(fs.readFileSync(legacyFile, "utf8"));
    const rows = normalizeRows(parsed);
    if (rows) {
      writeRowsToDisk(rows);
      return rows;
    }
  }

  if (fs.existsSync(legacyBackup)) {
    const parsed = tryParseJson(fs.readFileSync(legacyBackup, "utf8"));
    const rows = normalizeRows(parsed);
    if (rows) {
      writeRowsToDisk(rows);
      return rows;
    }
  }

  return null;
}

function writeRowsToDisk(rows) {
  if (!Array.isArray(rows)) return false;
  const file = dataFilePath();
  const backup = backupFilePath();
  const temp = `${file}.tmp`;
  const content = JSON.stringify(rows, null, 2);

  fs.writeFileSync(temp, content, "utf8");
  fs.renameSync(temp, file);
  fs.writeFileSync(backup, content, "utf8");
  return true;
}

function clearRowsOnDisk() {
  const file = dataFilePath();
  const backup = backupFilePath();
  const legacyFile = legacyDataFilePath();
  const legacyBackup = legacyBackupFilePath();
  if (fs.existsSync(file)) fs.unlinkSync(file);
  if (fs.existsSync(backup)) fs.unlinkSync(backup);
  if (fs.existsSync(legacyFile)) fs.unlinkSync(legacyFile);
  if (fs.existsSync(legacyBackup)) fs.unlinkSync(legacyBackup);
  return true;
}

function getStorageInfo() {
  const file = dataFilePath();
  const backup = backupFilePath();
  const legacyFile = legacyDataFilePath();
  const legacyBackup = legacyBackupFilePath();
  const fileExists = fs.existsSync(file);
  const backupExists = fs.existsSync(backup);
  const legacyFileExists = fs.existsSync(legacyFile);
  const legacyBackupExists = fs.existsSync(legacyBackup);

  return {
    appName: app.getName(),
    projectPath: __dirname,
    userDataPath: app.getPath("userData"),
    dataFile: file,
    backupFile: backup,
    legacyDataFile: legacyFile,
    legacyBackupFile: legacyBackup,
    dataFileExists: fileExists,
    backupFileExists: backupExists,
    legacyDataFileExists: legacyFileExists,
    legacyBackupFileExists: legacyBackupExists,
    dataFileSize: fileExists ? fs.statSync(file).size : 0,
    backupFileSize: backupExists ? fs.statSync(backup).size : 0,
    legacyDataFileSize: legacyFileExists ? fs.statSync(legacyFile).size : 0,
    legacyBackupFileSize: legacyBackupExists ? fs.statSync(legacyBackup).size : 0,
    dataFileMtime: fileExists ? fs.statSync(file).mtime.toISOString() : null,
    backupFileMtime: backupExists ? fs.statSync(backup).mtime.toISOString() : null,
    legacyDataFileMtime: legacyFileExists ? fs.statSync(legacyFile).mtime.toISOString() : null,
    legacyBackupFileMtime: legacyBackupExists ? fs.statSync(legacyBackup).mtime.toISOString() : null
  };
}

function startBackend() {
  const scriptPath = path.join(__dirname, "backend", "server.py");
  if (!fs.existsSync(scriptPath)) {
    console.error("[cgp] backend script not found:", scriptPath);
    return;
  }

  const pythonCmd = process.env.CGP_PYTHON || "python";
  backendProcess = spawn(pythonCmd, [scriptPath], {
    cwd: __dirname,
    windowsHide: true,
    stdio: ["ignore", "pipe", "pipe"]
  });

  backendProcess.stdout.on("data", (buf) => {
    console.log(String(buf).trim());
  });

  backendProcess.stderr.on("data", (buf) => {
    console.error(String(buf).trim());
  });

  backendProcess.on("exit", (code) => {
    console.log(`[cgp] python backend exited with code ${code}`);
    backendProcess = null;
  });
}

function stopBackend() {
  if (!backendProcess) return;
  try {
    backendProcess.kill();
  } catch {
  }
  backendProcess = null;
}

function loadRenderer(win) {
  const devUrl = process.env.CGP_WEB_URL;
  if (devUrl) {
    win.loadURL(devUrl);
    return;
  }
  win.loadFile(path.join(__dirname, "dist", "index.html"));
}

function createWindow() {
  const win = new BrowserWindow({
    width: 1280,
    height: 860,
    minWidth: 980,
    minHeight: 680,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false
    }
  });

  loadRenderer(win);
}

ipcMain.on("rows:read-sync", (event) => {
  event.returnValue = readRowsFromDisk();
});

ipcMain.on("rows:write-sync", (event, rows) => {
  event.returnValue = writeRowsToDisk(rows);
});

ipcMain.on("rows:clear-sync", (event) => {
  event.returnValue = clearRowsOnDisk();
});

ipcMain.on("rows:storage-info-sync", (event) => {
  event.returnValue = getStorageInfo();
});

app.whenReady().then(() => {
  startBackend();
  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("before-quit", () => {
  stopBackend();
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});
