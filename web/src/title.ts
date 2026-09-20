// Author: Claude (Anthropic) — this file is AI generated, see ../../docs/init.md.

import { useEffect } from "react";

/** What every page appends to, and what a bookmark of the site root reads. */
const SITE = "Géoplateforme catalogue — unofficial overview";

/**
 * Name the current page in the tab, the history and the bookmark.
 *
 * A single page application keeps the `<title>` of its entry document unless it
 * is told otherwise, which would make every route — and every record — share one
 * name in a history list. The word *unofficial* stays in it, since a search
 * result and a bookmark are exactly where the page is mistaken for the
 * catalogue's own.
 */
export function usePageTitle(name: string | null): void {
  useEffect(() => {
    document.title = name ? `${name} — ${SITE}` : SITE;
  }, [name]);
}
