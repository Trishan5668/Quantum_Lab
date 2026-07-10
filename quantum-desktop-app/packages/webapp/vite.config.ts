import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

const workspaceRoot = path.resolve(__dirname, "../..");

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
      // npm workspaces hoists deps to the monorepo root — point Vite there explicitly.
      react: path.resolve(workspaceRoot, "node_modules/react"),
      "react-dom": path.resolve(workspaceRoot, "node_modules/react-dom"),
      "react-router-dom": path.resolve(workspaceRoot, "node_modules/react-router-dom"),
    },
    dedupe: ["react", "react-dom", "react-router-dom"],
  },
  server: {
    port: 5173,
    strictPort: true,
    host: true,
  },
  build: {
    outDir: "dist",
    sourcemap: true,
    target: "es2022",
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
  },
});
