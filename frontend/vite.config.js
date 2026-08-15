import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// el backend FastAPI corre por defecto en http://localhost:8000 y expone la API
// bajo el prefijo /api. proxyeo /api -> backend conservando el prefijo (mismo
// esquema que en produccion, donde FastAPI sirve /api y el frontend estatico).
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
