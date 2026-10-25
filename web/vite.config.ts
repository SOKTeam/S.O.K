import { svelte } from "@sveltejs/vite-plugin-svelte";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "vitest/config";

// npm run dev: the interface on http://localhost:5173, the API of a
// sok-server running on SOK_API (http://localhost:8080 by default).
// --mode demo (npm run dev:demo, build:demo): the demo of the website, under
// /demo/, its server in the browser (src/demo), built in dist-demo.
export default defineConfig(({ mode }) => ({
  plugins: [tailwindcss(), svelte()],
  base: mode === "demo" ? "/demo/" : "/",
  server: {
    proxy: mode === "demo" ? undefined : { "/api": process.env.SOK_API ?? "http://localhost:8080" },
    // The demo reads the translation files of S.O.K, above web/.
    fs: { allow: [".."] },
  },
  build: {
    outDir: mode === "demo" ? "dist-demo" : "dist",
    emptyOutDir: true,
  },
  test: {
    include: ["src/**/*.test.ts"],
  },
}));
