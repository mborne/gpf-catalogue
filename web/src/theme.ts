// Author: Claude (Anthropic) — this file is AI generated, see ../../docs/init.md.

/** Key the chosen theme is remembered under, unchanged from the previous site. */
const KEY = "gpf-theme";

/* Browser storage can throw or come back empty (private window, blocked site
   data), and the page must render either way: a remembered theme is a
   convenience, never a requirement. */

export function storedTheme(): string | null {
  try {
    return localStorage.getItem(KEY);
  } catch {
    return null;
  }
}

/** Flip between light and dark, starting from whatever is currently shown. */
export function toggleTheme(): void {
  const dark =
    document.documentElement.dataset.theme === "dark" ||
    (!document.documentElement.dataset.theme &&
      window.matchMedia("(prefers-color-scheme: dark)").matches);
  const next = dark ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  try {
    localStorage.setItem(KEY, next);
  } catch {
    /* Not remembering it is the only consequence. */
  }
}

/** Apply the remembered theme, before anything is painted. */
export function applyStoredTheme(): void {
  const stored = storedTheme();
  if (stored) document.documentElement.dataset.theme = stored;
}
