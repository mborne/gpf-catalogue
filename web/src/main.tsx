// Author: Claude (Anthropic) — this file is AI generated, see ../../docs/init.md.

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router";

import { App } from "./App";
import "./styles.css";
import { applyStoredTheme } from "./theme";

applyStoredTheme();

/* `BASE_URL` is the deployment prefix Vite was built with — `/gpf-catalogue/` on
   GitHub Pages, `/` elsewhere. Handing it to the router as its basename is what
   makes `/gpf-catalogue/records/IGNF_BD-TOPO` and `/records/IGNF_BD-TOPO` the
   same route in two deployments of the same build system. */
const root = document.getElementById("root");
if (root) {
  createRoot(root).render(
    <StrictMode>
      <BrowserRouter basename={import.meta.env.BASE_URL}>
        <App />
      </BrowserRouter>
    </StrictMode>,
  );
}
