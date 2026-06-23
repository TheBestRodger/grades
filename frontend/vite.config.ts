/// <reference types="vitest" />

import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const apiProxyTarget = process.env.FRONTEND_API_PROXY_TARGET ?? "http://127.0.0.1:8010";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: "127.0.0.1",
    port: 5173,
    proxy: {
      "/api": apiProxyTarget,
    },
  },
  preview: {
    host: "0.0.0.0",
    port: 3000,
    proxy: {
      "/api": apiProxyTarget,
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: "./src/test/setupTests.ts",
    coverage: {
      provider: "v8",
      reporter: ["text", "html"],
      include: ["src/features/**/*.ts", "src/shared/**/*.ts"],
      exclude: ["src/**/*.test.ts", "src/test/**", "src/**/*.tsx"],
    },
  },
});
