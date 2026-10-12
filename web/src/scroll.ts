// Author: Claude (Anthropic) — this file is AI generated, see ../../docs/init.md.

import { useEffect, useLayoutEffect, useRef } from "react";
import { useLocation, useNavigationType } from "react-router";

/* Scroll position per history entry, for the lifetime of the application. A
   `Map` and not `sessionStorage`: it answers the Back button, and a reload gets
   a fresh set of entries anyway. */
const positions = new Map<string, number>();

/** How long a fragment waits for its heading: the catalogue is 1.2 MB to load. */
const HASH_TIMEOUT = 10_000;

/**
 * Scroll to the element a fragment names, once it exists.
 *
 * A pasted `/records/IGNF_ADMIN-EXPRESS#wfs` loads a document with no record in
 * it yet: the heading appears only once `catalogue.json` has arrived, which is
 * long after the browser gave up looking for it. So the element is waited for,
 * and the wait ends at the first scroll the reader makes, rather than yanking the
 * page from under them. The sticky top bar is subtracted, or the heading would
 * land underneath it.
 *
 * Returns a function cancelling the wait.
 */
function scrollToHash(hash: string): () => void {
  let id: string;
  try {
    id = decodeURIComponent(hash.slice(1));
  } catch {
    id = hash.slice(1);
  }

  const go = (): boolean => {
    const element = document.getElementById(id);
    if (!element) return false;
    const bar = document.querySelector(".topbar")?.getBoundingClientRect().height ?? 0;
    const top = element.getBoundingClientRect().top + window.scrollY - bar - 8;
    window.scrollTo(0, Math.max(0, top));
    return true;
  };
  if (go()) return () => {};

  const observer = new MutationObserver(() => {
    if (go()) stop();
  });
  const timer = window.setTimeout(() => stop(), HASH_TIMEOUT);
  const stop = () => {
    observer.disconnect();
    window.clearTimeout(timer);
    window.removeEventListener("wheel", stop);
    window.removeEventListener("touchmove", stop);
    window.removeEventListener("keydown", stop);
  };
  observer.observe(document.body, { childList: true, subtree: true });
  window.addEventListener("wheel", stop, { passive: true });
  window.addEventListener("touchmove", stop, { passive: true });
  window.addEventListener("keydown", stop);
  return stop;
}

/**
 * Put a new page at the top, and a page returned to back where it was left.
 *
 * A browser scrolls to the top of a document it just loaded, but a route change
 * loads no document: without this, following a link from halfway down `/records`
 * opens the record halfway down, which reads as a page that failed to render its
 * beginning. The three cases are not the same move:
 *
 * - **PUSH** — a new page, so the top of it. Opening a record, or a service on
 *   the coverage page. Unless the URL names a heading (`#wfs`): then that
 *   heading, which is also what a pasted link to one gets on the first load.
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
  const { key, hash } = useLocation();
  const navigationType = useNavigationType();
  const scrollY = useRef(0);
  const current = useRef<string | null>(null);
  // A wait for a heading belongs to one entry: the next navigation cancels it.
  // Held in a ref rather than returned as the effect cleanup, because the effect
  // returns early on a re-run for the same entry, and that would end the wait.
  const cancel = useRef<() => void>(() => {});

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
    // placed, and a deep link that was pasted must not be scrolled off — except
    // to the heading it names, which the browser could not find before render.
    const first = current.current === null;
    if (!first) positions.set(current.current as string, scrollY.current);
    current.current = key;
    cancel.current();
    cancel.current = () => {};
    if (navigationType === "REPLACE" && !first) return;

    const saved = navigationType === "POP" ? positions.get(key) : undefined;
    if (saved === undefined && hash) {
      cancel.current = scrollToHash(hash);
      return;
    }
    if (first) return;

    const target = saved ?? 0;
    window.scrollTo(0, target);
    scrollY.current = target;
  }, [key, hash, navigationType]);
}
