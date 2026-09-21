// Author: Claude (Anthropic) — this file is AI generated, see ../../../docs/init.md.

import { useMemo, type JSX } from "react";
import { Link } from "react-router";

import { cmp, recordPath } from "../format";
import type { CatalogueRecord } from "../types";

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
    () => [...new Set(record.links.map((link) => link.type))].sort(cmp),
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
      {protocols.map((protocol) => (
        <span className="badge protocol" key={protocol} title="access link published">
          {protocol}
        </span>
      ))}
    </Link>
  );
}
