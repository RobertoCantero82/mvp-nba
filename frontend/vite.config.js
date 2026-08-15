import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// base './' hace que las rutas de assets sean relativas: asi la web funciona tanto
// en la raiz de un Space de Hugging Face como bajo cualquier subcarpeta.
// no necesito proxy: la web lee el contenido de archivos JSON estaticos (data/).
export default defineConfig({
  base: "./",
  plugins: [react()],
});
