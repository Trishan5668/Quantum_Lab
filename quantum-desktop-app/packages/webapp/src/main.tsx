import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { AuthProvider } from "./auth/AuthProvider";
import { LoginModal } from "./auth/LoginModal";
import "katex/dist/katex.min.css";
import "./index.css";

const root = document.getElementById("root");
if (!root) {
  throw new Error("Root element #root not found in index.html");
}

ReactDOM.createRoot(root).render(
  <React.StrictMode>
    <AuthProvider>
      <App />
      <LoginModal />
    </AuthProvider>
  </React.StrictMode>,
);
