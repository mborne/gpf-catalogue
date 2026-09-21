// Author: Claude (Anthropic) — this file is AI generated, see ../../../docs/init.md.

import { useMemo, type JSX } from "react";
import { Link } from "react-router";

import { cmp, recordPath } from "../format";
import type { CatalogueRecord, LinkType } from "../types";

/* Two link types say nothing about what a record offers. `capabilities` is the
   static description of a service the record already badges — 129 entries, and
   no record publishes one without the service beside it — and `other` is what
   the URL did not let us type, 235 entries on which the badge would only repeat
   that the catalogue published a link. Dropping them leaves 14 rows with no
   protocol badge at all, which is what they had to say. Both types stay in the
   model and on the record page; only the scanning badges drop them. */
const UNBADGED: ReadonlySet<LinkType> = new Set(["capabilities", "other"]);

/**
 * One row of the result list: what is needed to decide whether to open it.
 *
 * The whole row is a link to `/records/{fileIdentifier}`. The previous site
 * expanded a `<details>` in place, which showed the same content but left the
 * record with no address of its own.
 */
export function RecordSummary({ record }: { record: CatalogueRecord }): JSX.Element {
  /* The protocols the record offers, once each: a record publishes up to 251
     links but at most seven distinct types, and "does this have a WFS?" is asked
     while scanning the list. The order is the one the record page groups by, so
     a badge sits where the section it points at will be. */
  const protocols = useMemo(
    () =>
      [...new Set(record.links.map((link) => link.type))]
        .filter((type) => !UNBADGED.has(type))
        .sort(cmp),
    [record.links],
  );

  return (
    <Link className="record-link" to={recordPath(record.fileIdentifier)}>
      <span className={record.title ? "record-title" : "record-title untitled"}>
        {record.title || "(no title published)"}
      </span>
      {/* The identifier is not shown: it repeats the title on most rows —
          `IGNF_BD-TOPO` next to "BD TOPO®" — and it is a file name, not a name.
          On the one record that publishes no title it is all there is to point
          at, so it stays there, and only there. */}
      {record.title ? null : <span className="record-id">{record.fileIdentifier}</span>}
      <span className="badge">{record.type}</span>
      {/* The scope rides next to the type rather than sitting in the detail list:
          "national or local?" is asked while scanning the list, not after opening a
          record. Only 136 of the 326 records cite one, so most rows carry none. */}
      {record.spatialScope ? (
        <span className="badge" title="INSPIRE spatial scope">
          {record.spatialScope}
        </span>
      ) : null}
      {record.suspectedTest ? (
        <span className="badge warn">suspected test</span>
      ) : null}
      {/* The protocols go on a line of their own: a record offering seven of them
          pushed the title, the type and the scope off the first line, so the row
          no longer started with what identifies it. */}
      {protocols.length > 0 ? (
        <span className="record-protocols">
          {protocols.map((protocol) => (
            <span className="badge protocol" key={protocol} title="access link published">
              {protocol}
            </span>
          ))}
        </span>
      ) : null}
    </Link>
  );
}
