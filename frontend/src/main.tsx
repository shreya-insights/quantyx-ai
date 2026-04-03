import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css";

// Apply persisted theme before first render to avoid flash
const saved = localStorage.getItem("quantyx-theme");
if (saved) {
  try {
    const { state } = JSON.parse(saved);
    if (state?.theme === "dark") {
      document.documentElement.classList.add("dark");
    }
  } catch {
    // ignore
  }
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
