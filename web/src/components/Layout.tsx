// Author: Claude (Anthropic) — this file is AI generated, see ../../../docs/init.md.

import type { JSX } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router";

import { useCatalogueState } from "../catalogue";
import { fmt } from "../format";
import { toggleTheme } from "../theme";

/** The three sections, in the order they answer questions about the catalogue. */
const TABS = [
  { to: "/overview", label: "Overview" },
  { to: "/records", label: "Records" },
  { to: "/quality", label: "Quality" },
];

/* Ahead of every figure on the site, because a catalogue overview published by an
   individual is easy to mistake for the catalogue's own. It sits in the layout
   rather than on each page, so no route can be reached without it.

   One line, and the line is a link: the warning has to be read on every route,
   the paragraph explaining it has to be read once. `/about` is that paragraph,
   with the room the banner never had. */
function Disclaimer(): JSX.Element {
  return (
    <p className="disclaimer" role="note">
      <Link className="disclaimer-link" to="/about">
        <strong>This is not an official Géoplateforme or IGN site.</strong>
        <span className="disclaimer-more">
          A personal experiment — what it is, how it is built, and where the
          authoritative catalogue is
        </span>
      </Link>
    </p>
  );
}

export function Layout(): JSX.Element {
  const { data } = useCatalogueState();
  const source = data?.stats.source ?? "data.geopf.fr/csw";
  /* Not on `/about`: that page opens with the same sentence, in full, and a
     banner linking to the page you are reading is noise. */
  const onAbout = useLocation().pathname === "/about";

  return (
    <>
      <header className="topbar">
        <div className="topbar-inner">
          <div>
            <h1>
              Géoplateforme catalogue <span className="tag-unofficial">unofficial</span>
            </h1>
            <p className="subtitle">
              {data
                ? `${fmt(data.stats.count)} resources harvested from ${data.stats.source}`
                : "Loading…"}
            </p>
          </div>
          <button
            type="button"
            className="ghost"
            aria-label="Switch colour theme"
            onClick={toggleTheme}
          >
            Theme
          </button>
        </div>
        {/* Real links, so a tab can be opened in a new window, bookmarked and shared —
            which three buttons toggling `hidden` could not be. */}
        <nav className="tabs">
          {TABS.map((tab) => (
            <NavLink
              key={tab.to}
              to={tab.to}
              className={({ isActive }) => (isActive ? "tab active" : "tab")}
            >
              {tab.label}
            </NavLink>
          ))}
        </nav>
      </header>

      <main>
        {onAbout ? null : <Disclaimer />}
        <Outlet />
      </main>

      <footer className="footer">
        <p>
          Unofficial. Built from <code>{source}</code> by{" "}
          <a
            href="https://github.com/mborne/gpf-catalogue"
            rel="noopener noreferrer"
            target="_blank"
          >
            gpf-catalogue
          </a>
          , an AI generated experiment. The site reads <code>catalogue.json</code> and{" "}
          <code>stats.json</code> next to it; nothing is sent anywhere.
        </p>
        <p>
          <Link to="/about">About this site</Link> ·{" "}
          <a
            href="https://mborne.github.io/mentions-legales/"
            rel="noopener noreferrer"
            target="_blank"
          >
            Mentions légales
          </a>
        </p>
      </footer>
    </>
  );
}
