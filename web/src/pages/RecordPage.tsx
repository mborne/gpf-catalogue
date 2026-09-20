// Author: Claude (Anthropic) — this file is AI generated, see ../../../docs/init.md.

import type { JSX } from "react";
import { Link, useParams } from "react-router";

import { useRecord } from "../catalogue";
import { RecordDetail } from "../components/RecordDetail";
import { usePageTitle } from "../title";

/**
 * One record, at `/records/{fileIdentifier}`.
 *
 * This route is the reason for the rewrite: a resource of the catalogue now has
 * an address that can be sent to someone, quoted in an issue, or — once phase 4
 * exists — returned by a search tool next to the data it describes.
 *
 * Identifiers are not tame: two carry spaces and accents, nine end in `.xml`,
 * and `id`/`ID` differ only by case. React Router hands back the decoded
 * segment, so the lookup is on the identifier as the catalogue publishes it, and
 * the match stays case sensitive.
 */
export function RecordPage(): JSX.Element {
  const { fileIdentifier } = useParams();
  const found = useRecord(fileIdentifier);
  usePageTitle(found ? (found.record.title ?? found.record.fileIdentifier) : "Unknown record");

  if (!found) {
    return (
      <section className="card">
        <h2>No record with this identifier</h2>
        <p className="caption">
          <code>{fileIdentifier}</code> is not in this copy of the catalogue. It may
          have been removed since the last weekly harvest, or never have converted —
          10 of the 336 published records do not reach the pivot catalogue, and the{" "}
          <Link to="/quality">Quality page</Link> says which and why.
        </p>
        <p className="caption">
          <Link to="/records">Back to the records</Link>
        </p>
      </section>
    );
  }

  const { record, facets } = found;
  return (
    <article className="card record-page">
      <p className="breadcrumb">
        <Link to="/records">Records</Link>
      </p>
      <h2 className={record.title ? "record-heading" : "record-heading untitled"}>
        {record.title || "(no title published)"}
      </h2>
      <p className="record-head-meta">
        <span className="badge">{record.type}</span>
        {record.spatialScope ? (
          <span className="badge" title="INSPIRE spatial scope">
            {record.spatialScope}
          </span>
        ) : null}
        {record.suspectedTest ? <span className="badge warn">suspected test</span> : null}
        <code className="record-id">{record.fileIdentifier}</code>
      </p>
      <RecordDetail record={record} facets={facets} />
    </article>
  );
}
