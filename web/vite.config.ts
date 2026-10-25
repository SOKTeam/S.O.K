import { svelte } from "@sveltejs/vite-plugin-svelte";
import tailwindcss from "@tailwindcss/vite";
import type { Plugin } from "vite";
import { defineConfig } from "vitest/config";

/** The website that hosts the demo; its preview image is /og-demo.png there. */
const SITE = "https://sokfromsokteam.vercel.app";

/** The preview of a link to the demo (Open Graph, Twitter), in its page only. */
function demoPreview(): Plugin {
  const title = "S.O.K Server — Live demo";
  const description =
    "Try the web interface of S.O.K Server in your browser, with an example library. Nothing to install.";
  const tags: Record<string, string> = {
    "og:type": "website",
    "og:site_name": "S.O.K",
    "og:url": `${SITE}/demo`,
    "og:title": title,
    "og:description": description,
    "og:image": `${SITE}/og-demo.png`,
    "og:image:width": "1200",
    "og:image:height": "630",
    "og:image:alt": "S.O.K Server, live demo",
    "twitter:card": "summary_large_image",
    "twitter:title": title,
    "twitter:description": description,
    "twitter:image": `${SITE}/og-demo.png`,
  };
  return {
    name: "sok-demo-preview",
    transformIndexHtml: (html) => ({
      html: html.replace(/<title>.*<\/title>/, `<title>${title}</title>`),
      tags: [
        { tag: "meta", attrs: { name: "description", content: description }, injectTo: "head" },
        ...Object.entries(tags).map(([name, content]) => ({
          tag: "meta",
          attrs: name.startsWith("og:") ? { property: name, content } : { name, content },
          injectTo: "head" as const,
        })),
      ],
    }),
  };
}

// npm run dev: the interface on http://localhost:5173, the API of a
// sok-server running on SOK_API (http://localhost:8080 by default).
// --mode demo (npm run dev:demo, build:demo): the demo of the website, under
// /demo/, its server in the browser (src/demo), built in dist-demo.
export default defineConfig(({ mode }) => ({
  plugins: [tailwindcss(), svelte(), ...(mode === "demo" ? [demoPreview()] : [])],
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
