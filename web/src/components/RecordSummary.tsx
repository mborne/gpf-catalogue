// Author: Claude (Anthropic) — this file is AI generated, see ../../../docs/init.md.

import type { JSX } from "react";
import { Link } from "react-router";

import { recordPath } from "../format";
import type { CatalogueRecord } from "../types";

/**
 * One row of the result list: what is needed to decide whether to open it.
 *
 * The whole row is a link to `/records/{fileIdentifier}`. The previous site
 * expanded a `<details>` in place, which showed the same content but left the
 * record with no address of its own.
 */
export function RecordSummary({ record }: { record: CatalogueRecord }): JSX.Element {
  return (
    <Link className="record-link" to={recordPath(record.fileIdentifier)}>
      <span className={record.title ? "record-title" : "record-title untitled"}>
        {record.title || "(no title published)"}
      </span>
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
      <span className="record-id">{record.fileIdentifier}</span>
    </Link>
  );
}
