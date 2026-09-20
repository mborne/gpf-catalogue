// Author: Claude (Anthropic) — this file is AI generated, see ../docs/init.md.

import { createReadStream, existsSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import react from "@vitejs/plugin-react";
import { defineConfig, type Plugin } from "vite";

/* The deployment prefix is a build time value, because the routes are real paths:
   `/records/IGNF_BD-TOPO` has to resolve its script against the site root, not
   against the record it is showing, which rules out relative asset URLs. GitHub
   Pages serves this repository under `/gpf-catalogue/`, a local `http.server`
   under `/`, so the prefix is passed in rather than hard coded — the Pages
   workflow sets it, everything else gets `/`.

   `import.meta.env.BASE_URL` carries the same value into the application, where
   react-router takes it as its basename and the two JSON documents are fetched
   from it. */
const base = process.env.VITE_BASE ?? "/";

const here = dirname(fileURLToPath(import.meta.url));

/** The two documents the application reads, served to `vite dev` from `data/`. */
const DATA = ["catalogue.json", "stats.json"];

/**
 * Serve `data/catalogue.json` and `data/stats.json` at the root, in development.
 *
 * The built site carries its own copy of both, written beside it by
 * `scripts/build_site.py`. The dev server has no such copy, and putting `data/`
 * in `publicDir` would copy the whole 13 MB mirror into every build — so they are
 * read from where the pipeline wrote them, and only while developing.
 */
function devData(): Plugin {
  return {
    name: "gpf-catalogue-dev-data",
    apply: "serve",
    configureServer(server) {
      server.middlewares.use((request, response, next) => {
        const name = (request.url ?? "").split("?")[0]?.replace(/^\//, "") ?? "";
        const path = resolve(here, "..", "data", name);
        if (!DATA.includes(name) || !existsSync(path)) return next();
        response.setHeader("content-type", "application/json");
        createReadStream(path).pipe(response);
      });
    },
  };
}

export default defineConfig({
  base,
  plugins: [react(), devData()],
  build: {
    // The site is published as a build artifact and read by humans looking at what
    // the page does; a source map would double its size for no one.
    sourcemap: false,
    // One chunk. At this size splitting only adds round trips, and the site has to
    // work behind any static host without HTTP/2 push or preload hints.
    chunkSizeWarningLimit: 900,
  },
});
