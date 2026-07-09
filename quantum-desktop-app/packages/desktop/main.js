"use strict";

const { app, BrowserWindow, shell } = require("electron");
const path = require("node:path");
const { spawn } = require("node:child_process");

const DEV_URL = process.env.QUANTUMLAB_DEV_URL || "http://127.0.0.1:5173/app";
const PROD_INDEX = path.resolve(__dirname, "..", "webapp", "dist", "index.html");
const isDev = !app.isPackaged;

let mainWindow = null;
let apiProcess = null;

function spawnApiServer() {
  if (process.env.QUANTUMLAB_NO_API === "1") return;
  const apiCmd = process.env.QUANTUMLAB_API_CMD || "python";
  const apiArgs = (
    process.env.QUANTUMLAB_API_ARGS ||
    "-m uvicorn app.main:app --host 127.0.0.1 --port 8765"
  ).split(" ");
  apiProcess = spawn(apiCmd, apiArgs, {
    cwd:
      process.env.QUANTUMLAB_API_CWD ||
      path.resolve(__dirname, "..", "..", "..", "fastapi-server"),
    stdio: ["ignore", "inherit", "inherit"],
  });
  apiProcess.on("error", (err) => {
    console.error("[quantumlab] failed to spawn api:", err);
  });
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1480,
    height: 960,
    minWidth: 1120,
    minHeight: 720,
    title: "QuantumLab",
    backgroundColor: "#0a0b0f",
    show: false,
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      webSecurity: true,
    },
  });

  mainWindow.once("ready-to-show", () => mainWindow?.show());

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    void shell.openExternal(url);
    return { action: "deny" };
  });

  if (isDev) {
    void mainWindow.loadURL(DEV_URL);
  } else {
    void mainWindow.loadFile(PROD_INDEX, { hash: "/app" });
  }

  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

app.whenReady().then(() => {
  spawnApiServer();
  createWindow();
  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

app.on("before-quit", () => {
  if (apiProcess && !apiProcess.killed) {
    apiProcess.kill();
  }
});
