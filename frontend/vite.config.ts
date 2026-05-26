import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "127.0.0.1",
    port: 19000,
    proxy: {
      "/api": "http://127.0.0.1:19001",
      "/health": "http://127.0.0.1:19001"
    }
  }
});
