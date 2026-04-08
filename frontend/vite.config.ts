import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // Dev proxy → local FastAPI on 8000
      "/api": {
        // VITE_API_TARGET overrides the default when running inside Docker Compose
        // (docker-compose.yml sets it to http://api:8000)
        target: process.env.VITE_API_TARGET ?? "http://localhost:8000",
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
  build: {
    outDir: "dist",
    sourcemap: true,
  },
});
