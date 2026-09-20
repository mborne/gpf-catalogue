// Author: Claude (Anthropic) — this file is AI generated, see ../../../docs/init.md.

import { useMemo, type JSX, type ReactNode } from "react";

import { cartesGouvUrl, cmp, cswUrl, fmt } from "../format";
import { Markdown } from "../markdown";
import type { CatalogueRecord, Link, RecordFacets } from "../types";

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
  // The links are shown raw, one row per entry the catalogue published — nothing is
  // folded, because the repetition, the empty names and the same endpoint under four
  // spellings are what the source actually looks like. They are only *sectioned* by
  // protocol: a record publishing 178 links repeats its type on 178 rows, which is a
  // column of noise on a table that is already too wide for a phone. The heading says
  // it once per group instead, and the rows keep their order — URL, then name, then
  // description — inside it.
  const groups = useMemo(() => {
    const byType = new Map<string, Link[]>();
    for (const link of record.links) {
      const group = byType.get(link.type);
      if (group) group.push(link);
      else byType.set(link.type, [link]);
    }
    return [...byType.entries()]
      .sort(([a], [b]) => cmp(a, b))
      .map(([type, entries]) => ({
        type,
        entries: entries.sort(
          (a, b) =>
            cmp(a.url, b.url) ||
            cmp(a.name, b.name) ||
            cmp(a.description, b.description),
        ),
      }));
  }, [record.links]);

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

      {/* The image is served by the catalogue, i.e. a third party: it is shown as
          an image and nothing more — no referrer, and never injected as markup. */}
      {record.thumbnailUrl ? (
        <img
          alt=""
          className="thumbnail"
          loading="lazy"
          referrerPolicy="no-referrer"
          src={record.thumbnailUrl}
        />
      ) : null}

      {record.abstract ? (
        <div className="abstract">
          <Markdown text={record.abstract} />
        </div>
      ) : null}

      <dl className="pairs">
        <Pair term="Edition" value={record.edition} />
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
        <Pair term="Update frequency" value={record.updateFrequency} />
        {record.temporalStart || record.temporalEnd ? (
          <Pair
            term="Covers"
            value={`${record.temporalStart || "?"} → ${record.temporalEnd || "?"}`}
          />
        ) : null}
        {record.bbox ? (
          <Pair
            term={
              record.extents.length > 1
                ? `Bounding box (W, S, E, N), union of ${fmt(record.extents.length)} extents`
                : "Bounding box (W, S, E, N)"
            }
            value={record.bbox.join(", ")}
          />
        ) : null}
        <Pair
          term="Topic categories"
          value={record.topicCategories.join(", ")}
        />
        <Pair term="INSPIRE themes" value={record.inspireThemes.join(", ")} />
        <Pair term="Keywords" value={record.keywords.join(", ")} />
        <Pair term="Purpose" value={record.purpose} />
        <Pair term="Lineage" value={record.lineage} />
      </dl>

      {/* Only worth a table when the union hides something: a single extent is
          already fully described by the bounding box above. */}
      {record.extents.length > 1 ? (
        <>
          <h3 className="section-title">{`Extents (${fmt(record.extents.length)})`}</h3>
          <p className="caption">
            The bounding box above is the union of these. It can be far larger than
            what the resource covers.
          </p>
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th scope="col">Zone</th>
                  <th scope="col">Code</th>
                  <th scope="col">W, S, E, N</th>
                </tr>
              </thead>
              <tbody>
                {record.extents.map((extent, position) => (
                  <tr key={`${extent.code}-${extent.name}-${position}`}>
                    <td>{extent.name || "—"}</td>
                    <td className="name" title={extent.codeSpace || undefined}>
                      {extent.code || "—"}
                    </td>
                    <td className="name">{extent.bbox.join(", ")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : null}

      {record.links.length ? (
        <>
          <h3 className="section-title">
            {`Access links (${fmt(record.links.length)})`}
          </h3>
          {groups.map((group) => (
            <section key={group.type}>
              <h4 className="link-group">
                {group.type}
                <span className="link-group-count">
                  {`(${fmt(group.entries.length)})`}
                </span>
              </h4>
              <div className="table-wrap">
                <table className="table links-table">
                  <thead>
                    <tr>
                      <th scope="col">URL</th>
                      <th scope="col">Name</th>
                      <th scope="col">Description</th>
                    </tr>
                  </thead>
                  <tbody>
                    {group.entries.map((link, position) => (
                      <tr key={`${link.url}-${link.name}-${position}`}>
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
            </section>
          ))}
        </>
      ) : (
        <p className="caption">This record publishes no access link at all.</p>
      )}
    </div>
  );
}
