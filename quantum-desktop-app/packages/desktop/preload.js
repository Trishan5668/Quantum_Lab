"use strict";

const { contextBridge } = require("electron");

contextBridge.exposeInMainWorld("quantumlab", {
  platform: process.platform,
  versions: {
    electron: process.versions.electron,
    chrome: process.versions.chrome,
    node: process.versions.node,
  },
  apiBaseUrl: "http://127.0.0.1:8765/api/v1",
});
