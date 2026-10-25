import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite-plus";

export default defineConfig({
  publicDir: "static",
  resolve: { alias: { "@": new URL("./src", import.meta.url).pathname } },
  build: { outDir: "build" },
  server: {
    proxy: {
      "/api": "http://127.0.0.1:8000",
    },
  },
  fmt: {},
  lint: {
    jsPlugins: [{ name: "vite-plus", specifier: "vite-plus/oxlint-plugin" }],
    rules: { "vite-plus/prefer-vite-plus-imports": "error" },
    options: { typeAware: true, typeCheck: false },
  },
  plugins: [react(), tailwindcss()],
});
