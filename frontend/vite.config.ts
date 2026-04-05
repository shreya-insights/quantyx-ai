import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "./src") },
  },
  optimizeDeps: {
    include: ["react-window"],
  },
  server: {
    port: 3000,
    proxy: {
      "/api": {
        // 127.0.0.1 avoids macOS resolving `localhost` to ::1 while uvicorn listens on IPv4.
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        secure: false,
        ws: true,
      },
    },
  },
  build: {
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes("node_modules")) {
            if (id.includes("recharts") || id.includes("d3-")) return "charts";
            if (id.includes("monaco-editor") || id.includes("@monaco-editor")) return "editor";
            if (id.includes("@tanstack")) return "query";
            if (id.includes("zustand")) return "zustand";
            if (id.includes("react-dom") || id.includes("react-router") || id.includes("react")) return "vendor";
          }
        },
      },
    },
  },
});
