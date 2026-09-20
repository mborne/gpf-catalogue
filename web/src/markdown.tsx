// Author: Claude (Anthropic) — this file is AI generated, see ../../docs/init.md.

/* Abstracts are written in Markdown — 94 of the 326 use `**bold**`, 36 carry a
   list, 16 a link — and showing the asterisks is showing the source's markup
   rather than its text. Only abstracts: link names and descriptions are left
   alone, because 155 of them contain `*` or `_` inside a layer name such as
   `trichls_s_d51_gpkg_07-10-2024_wfs`, which any renderer would mangle, and the
   links table is meant to show the data raw.

   The text comes from a third party service, so nothing here ever builds HTML
   from it: every branch produces React elements, and anything unrecognised stays
   a string. `dangerouslySetInnerHTML` is never used, which is the React spelling
   of the rule the page has always followed — a `<script>` in an abstract is
   displayed, never run. */

import type { JSX, ReactNode } from "react";

/** The HTML escapes the catalogue leaves behind in its own text. */
const ENTITIES: Record<string, string> = {
  amp: "&",
  lt: "<",
  gt: ">",
  quot: '"',
  apos: "'",
  "#39": "'",
  nbsp: " ",
};

/** Inline constructs, tried in this order: code wins over emphasis, bold over italic. */
const INLINE =
  /`([^`]+)`|\*\*([^*]+)\*\*|\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)|\*([^*\n]+)\*|(https?:\/\/[^\s<>()]+)/g;

/** Undo what the source escaped twice, and turn its stray `<br>` into line breaks. */
function normalise(text: string): string {
  return text
    .replace(/<br\s*\/?>/gi, "\n")
    .replace(/&(amp|lt|gt|quot|apos|#39|nbsp);/g, (whole, name: string) =>
      name in ENTITIES ? (ENTITIES[name] as string) : whole,
    );
}

/** An external link, built rather than written: only http(s) URLs reach here. */
function externalLink(href: string, text: string, key: number): JSX.Element {
  return (
    <a key={key} href={href} rel="noopener noreferrer" target="_blank">
      {text}
    </a>
  );
}

/** Turn one line of Markdown into strings and the few elements it allows. */
function inlineNodes(text: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  let last = 0;
  let match: RegExpExecArray | null;
  INLINE.lastIndex = 0;
  while ((match = INLINE.exec(text)) !== null) {
    if (match.index > last) nodes.push(text.slice(last, match.index));
    const key = match.index;
    if (match[1] !== undefined) nodes.push(<code key={key}>{match[1]}</code>);
    else if (match[2] !== undefined) nodes.push(<strong key={key}>{match[2]}</strong>);
    else if (match[3] !== undefined)
      nodes.push(externalLink(match[4] as string, match[3], key));
    else if (match[5] !== undefined) nodes.push(<em key={key}>{match[5]}</em>);
    else nodes.push(externalLink(match[6] as string, match[6] as string, key));
    last = match.index + match[0].length;
  }
  if (last < text.length) nodes.push(text.slice(last));
  return nodes;
}

/**
 * Render an abstract as paragraphs, lists and headings.
 *
 * Blank lines separate blocks, consecutive lines join into one paragraph, and
 * consecutive bullets into one list — which is what the catalogue writes: BD
 * TOPO lists its themes as seven ` - ` lines in a row.
 */
export function Markdown({ text }: { text: string }): JSX.Element {
  const blocks: ReactNode[] = [];
  let paragraph: string[] = [];
  let items: ReactNode[][] = [];
  let listTag: "ul" | "ol" | null = null;

  const flushParagraph = () => {
    if (!paragraph.length) return;
    blocks.push(<p key={blocks.length}>{inlineNodes(paragraph.join(" "))}</p>);
    paragraph = [];
  };
  const flushList = () => {
    if (listTag) {
      const children = items.map((item, position) => <li key={position}>{item}</li>);
      blocks.push(
        listTag === "ul" ? (
          <ul key={blocks.length} className="md-list">
            {children}
          </ul>
        ) : (
          <ol key={blocks.length} className="md-list">
            {children}
          </ol>
        ),
      );
    }
    items = [];
    listTag = null;
  };

  for (const raw of normalise(text).split("\n")) {
    const line = raw.trim();
    if (!line) {
      flushParagraph();
      flushList();
      continue;
    }
    const heading = line.match(/^#{1,6}\s+(.*)$/);
    const bullet = line.match(/^[-*+]\s+(.*)$/);
    const numbered = line.match(/^\d+[.)]\s+(.*)$/);

    if (heading) {
      flushParagraph();
      flushList();
      blocks.push(
        <h4 key={blocks.length} className="md-heading">
          {inlineNodes(heading[1] as string)}
        </h4>,
      );
    } else if (bullet || numbered) {
      flushParagraph();
      const tag = bullet ? "ul" : "ol";
      if (listTag !== tag) {
        flushList();
        listTag = tag;
      }
      items.push(inlineNodes(((bullet || numbered) as RegExpMatchArray)[1] as string));
    } else {
      flushList();
      paragraph.push(line);
    }
  }
  flushParagraph();
  flushList();

  return <>{blocks}</>;
}
