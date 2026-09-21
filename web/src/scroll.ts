// Author: Claude (Anthropic) — this file is AI generated, see ../../docs/init.md.

import { useEffect, useLayoutEffect, useRef } from "react";
import { useLocation, useNavigationType } from "react-router";

/* Scroll position per history entry, for the lifetime of the application. A
   `Map` and not `sessionStorage`: it answers the Back button, and a reload gets
   a fresh set of entries anyway. */
const positions = new Map<string, number>();

/**
 * Put a new page at the top, and a page returned to back where it was left.
 *
 * A browser scrolls to the top of a document it just loaded, but a route change
 * loads no document: without this, following a link from halfway down `/records`
 * opens the record halfway down, which reads as a page that failed to render its
 * beginning. The three cases are not the same move:
 *
 * - **PUSH** — a new page, so the top of it. Opening a record, or a service on
 *   the coverage page.
 * - **POP** — a page already seen, so where it was left. Coming back from a
 *   record to the result list must land on the row that was clicked, not on the
 *   filters above it.
 * - **REPLACE** — not a page change at all. A filter change replaces the history
 *   entry rather than pushing one (see `docs/overview.md`), and moving the page
 *   under someone typing in the search box would be the opposite of helpful.
 *
 * The browser's own restoration is turned off, because it would fight all three:
 * it restores against a document that had not rendered this route yet.
 */
export function useScrollRestoration(): void {
  const { key } = useLocation();
  const navigationType = useNavigationType();
  const scrollY = useRef(0);
  const current = useRef<string | null>(null);

  useEffect(() => {
    const previous = history.scrollRestoration;
    history.scrollRestoration = "manual";
    return () => {
      history.scrollRestoration = previous;
    };
  }, []);

  /* One listener for the whole run, tracking where the page is. The layout
     effect below reads it *before* it moves the page, which is the only moment
     the outgoing position is still the one on screen — a listener rebound per
     entry would instead record the position this hook just scrolled to. */
  useEffect(() => {
    const track = () => {
      scrollY.current = window.scrollY;
    };
    track();
    window.addEventListener("scroll", track, { passive: true });
    return () => window.removeEventListener("scroll", track);
  }, []);

  // Layout, not passive: the move has to happen before the browser paints, or
  // the new page is shown at the old offset and then jumps.
  useLayoutEffect(() => {
    if (current.current === key) return;

    // The first run is the document the browser just loaded: it is already
    // placed, and a deep link that was pasted must not be scrolled off.
    const first = current.current === null;
    if (!first) positions.set(current.current as string, scrollY.current);
    current.current = key;
    if (first || navigationType === "REPLACE") return;

    const target = navigationType === "POP" ? (positions.get(key) ?? 0) : 0;
    window.scrollTo(0, target);
    scrollY.current = target;
  }, [key, navigationType]);
}
