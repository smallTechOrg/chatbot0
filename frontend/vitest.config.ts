import { resolve } from "path";
import { defineConfig } from "vitest/config";

export default defineConfig({
  resolve: { alias: { "@": resolve(__dirname, "src") } },
  esbuild: { jsx: "automatic" },
  test: { environment: "jsdom", include: ["src/**/*.test.{ts,tsx}"] },
});
