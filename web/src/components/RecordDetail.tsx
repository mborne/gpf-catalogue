// Author: Claude (Anthropic) — this file is AI generated, see ../../../docs/init.md.

import { useMemo, type JSX, type ReactNode } from "react";

import { cartesGouvUrl, cmp, cswUrl, fmt } from "../format";
import { Markdown } from "../markdown";
import type { CatalogueRecord, RecordFacets } from "../types";

function Pair({ term, value }: { term: string; value: ReactNode }): JSX.Element | null {
  if (!value) return null;
  return (
    <div className="pair">
      <dt>{term}</dt>
      <dd>{value}</dd>
    </div>
  );
}

function External({ href, children }: { href: string; children: ReactNode }) {
  return (
    <a href={href} rel="noopener noreferrer" target="_blank">
      {children}
    </a>
  );
}

/** Everything the catalogue published about one resource. */
export function RecordDetail({
  record,
  facets,
}: {
  record: CatalogueRecord;
  facets: RecordFacets | null;
}): JSX.Element {
  // The links are shown raw, one row per entry the catalogue published, sorted by
  // protocol then URL then name. Grouping or tidying them here would hide what the
  // source actually looks like — the repetition, the empty names, the same endpoint
  // under four spellings — and that mess is worth seeing.
  const links = useMemo(
    () =>
      [...record.links].sort(
        (a, b) =>
          cmp(a.type, b.type) ||
          cmp(a.url, b.url) ||
          cmp(a.name, b.name) ||
          cmp(a.description, b.description),
      ),
    [record.links],
  );

  return (
    <div className="record-body">
      {/* Right under the title: the two places the record itself lives, so anything
          below can be checked against the source without hunting for it. */}
      <p className="sources">
        <span className="badge">source</span>
        <External href={cartesGouvUrl(record.fileIdentifier, record.type)}>
          cartes.gouv.fr
        </External>
        <External href={cswUrl(record.fileIdentifier)}>metadata record (XML)</External>
      </p>

      {record.abstract ? (
        <div className="abstract">
          <Markdown text={record.abstract} />
        </div>
      ) : null}

      <dl className="pairs">
        <Pair term="Producer, as published" value={record.producer} />
        <Pair term="Contact" value={record.contactEmail} />
        <Pair term="Publisher (email domain)" value={facets?.publisher} />
        <Pair term="Licence" value={record.licence} />
        <Pair term="Licence family" value={facets?.licenceFamily} />
        <Pair term="Access constraint" value={record.accessConstraint} />
        <Pair term="Spatial scope" value={record.spatialScope} />
        <Pair term="Created" value={record.created} />
        <Pair term="Published" value={record.published} />
        <Pair term="Revised" value={record.revised} />
        {record.temporalStart || record.temporalEnd ? (
          <Pair
            term="Covers"
            value={`${record.temporalStart || "?"} → ${record.temporalEnd || "?"}`}
          />
        ) : null}
        {record.bbox ? (
          <Pair term="Bounding box (W, S, E, N)" value={record.bbox.join(", ")} />
        ) : null}
        <Pair
          term="Topic categories"
          value={record.topicCategories.join(", ")}
        />
        <Pair term="INSPIRE themes" value={record.inspireThemes.join(", ")} />
        <Pair term="Keywords" value={record.keywords.join(", ")} />
      </dl>

      {links.length ? (
        <>
          <h3 className="section-title">{`Access links (${fmt(links.length)})`}</h3>
          <div className="table-wrap">
            <table className="table links-table">
              <thead>
                <tr>
                  <th scope="col">Protocol</th>
                  <th scope="col">URL</th>
                  <th scope="col">Name</th>
                  <th scope="col">Description</th>
                </tr>
              </thead>
              <tbody>
                {links.map((link, position) => (
                  <tr key={`${link.type}-${link.url}-${link.name}-${position}`}>
                    <td className="protocol">{link.type}</td>
                    <td className="url">
                      <External href={link.url}>{link.url}</External>
                    </td>
                    <td className="name">{link.name || "—"}</td>
                    <td>{link.description || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : (
        <p className="caption">This record publishes no access link at all.</p>
      )}
    </div>
  );
}
