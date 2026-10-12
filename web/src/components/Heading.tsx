// Author: Claude (Anthropic) — this file is AI generated, see ../../../docs/init.md.

import type { JSX, ReactNode } from "react";
import { Link, useLocation } from "react-router";

/**
 * The fragment a heading is addressed by: lowercase, words joined by `-`.
 *
 * Only for headings whose text is fixed. A heading that carries a count — "298
 * WMTS layers no record describes" — would change address with every harvest, so
 * it is given an explicit `id` instead.
 */
export function slug(text: string): string {
  return text
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
}

/**
 * A heading that can be linked to: `/records/IGNF_ADMIN-EXPRESS#wfs` opens the
 * record on its WFS layers, which is what an issue or a message wants to cite.
 *
 * The `#` is a router link rather than a bare `href="#…"`: a bare fragment would
 * reach the router as a POP, and `useScrollRestoration` would answer it by
 * restoring an offset instead of going to the heading. Through the router it is a
 * PUSH, so Back still returns to where the reader was.
 */
export function Heading({
  level,
  id,
  className,
  children,
}: {
  level: 2 | 3 | 4;
  id: string;
  className?: string;
  children: ReactNode;
}): JSX.Element {
  const { pathname, search } = useLocation();
  const Tag = `h${level}` as const;
  return (
    <Tag id={id} className={className ? `${className} anchored` : "anchored"}>
      {children}
      <Link
        className="anchor"
        to={{ pathname, search, hash: `#${id}` }}
        aria-label="Link to this section"
      >
        #
      </Link>
    </Tag>
  );
}
