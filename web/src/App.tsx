// Author: Claude (Anthropic) — this file is AI generated, see ../../docs/init.md.

import type { JSX } from "react";
import { Navigate, Route, Routes } from "react-router";

import { CatalogueProvider, useCatalogueState } from "./catalogue";
import { Layout } from "./components/Layout";
import { AboutPage } from "./pages/AboutPage";
import { CoveragePage } from "./pages/CoveragePage";
import { CoverageServicePage } from "./pages/CoverageServicePage";
import { OverviewPage } from "./pages/OverviewPage";
import { QualityPage } from "./pages/QualityPage";
import { RecordPage } from "./pages/RecordPage";
import { RecordsPage } from "./pages/RecordsPage";

/* The routes are the point of this application: `/records/IGNF_BD-TOPO` is an
   address that can be sent to someone. `/` redirects to `/overview` rather than
   rendering it, so that the section a visitor is looking at is always written in
   the URL — including the first one. */

/** Pages render only once the catalogue is in: every one of them reads it. */
function Loaded({ children }: { children: JSX.Element }): JSX.Element {
  const { data, error } = useCatalogueState();
  if (error) {
    return (
      <p className="notice">
        {`${error} — the site reads catalogue.json and stats.json next to it, over HTTP. Try: uv run scripts/serve_site.py`}
      </p>
    );
  }
  if (!data) return <p className="result-count">Loading the catalogue…</p>;
  return children;
}

export function App(): JSX.Element {
  return (
    <CatalogueProvider>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Navigate to="/overview" replace />} />
          <Route
            path="overview"
            element={
              <Loaded>
                <OverviewPage />
              </Loaded>
            }
          />
          <Route
            path="records"
            element={
              <Loaded>
                <RecordsPage />
              </Loaded>
            }
          />
          <Route
            path="records/:fileIdentifier"
            element={
              <Loaded>
                <RecordPage />
              </Loaded>
            }
          />
          <Route
            path="quality"
            element={
              <Loaded>
                <QualityPage />
              </Loaded>
            }
          />
          <Route
            path="coverage"
            element={
              <Loaded>
                <CoveragePage />
              </Loaded>
            }
          />
          {/* The lists of what is not described are long enough to be a page, and
              a link to "the WMTS layers nobody documented" is worth sending to
              someone — which a section of a longer page could not be. */}
          <Route
            path="coverage/:service"
            element={
              <Loaded>
                <CoverageServicePage />
              </Loaded>
            }
          />
          {/* Outside `Loaded`: it is the page that says what the site is, which is
              exactly what is worth reaching when the two documents fail to load. */}
          <Route path="about" element={<AboutPage />} />
          {/* A static host answers an unknown path with the entry page, so an
              unknown route reaches the application rather than the host's 404.
              It lands on the overview instead of a dead end. */}
          <Route path="*" element={<Navigate to="/overview" replace />} />
        </Route>
      </Routes>
    </CatalogueProvider>
  );
}
