// Author: Claude (Anthropic) — this file is AI generated, see ../../../docs/init.md.

import type { JSX } from "react";
import { Link } from "react-router";

import { useCatalogue } from "../catalogue";
import { BarChart, ChartCard } from "../components/Chart";
import { fmt, recordPath } from "../format";
import { usePageTitle } from "../title";

export function QualityPage(): JSX.Element {
  const { stats } = useCatalogue();
  const quality = stats.quality;
  usePageTitle("Quality");

  const rows: [string, string | number][] = [
    ["Records declaring no licence", quality.undeclaredLicence],
    [
      "Records declaring no limitation on public access",
      quality.undeclaredAccessConstraint,
    ],
    ["Records citing no INSPIRE spatial scope", quality.undeclaredSpatialScope],
    [
      "Links carrying neither a name nor a description",
      `${fmt(quality.linksWithoutName)} of ${fmt(quality.linksTotal)}`,
    ],
    [
      "Links carrying no description",
      `${fmt(quality.linksWithoutDescription)} of ${fmt(quality.linksTotal)}`,
    ],
    [
      "Distinct spellings of producer, for far fewer organisations",
      quality.distinctProducers,
    ],
    ["Records offering no access link at all", quality.recordsWithoutLinks],
    ["Records flagged as test publications", quality.suspectedTests.length],
    ["Records published with no title", quality.missingTitle],
    ["Records published with no abstract", quality.missingAbstract],
  ];

  return (
    <>
      <p className="lead">
        What the source metadata is missing. These are properties of the Géoplateforme
        catalogue, not defects of this pipeline; they are published so that they can be
        acted upon.
      </p>

      <ChartCard
        title="Field coverage of the pivot model"
        wide
        caption="How often each optional field is actually filled in. Read from the model itself, so a new field is measured without being registered anywhere."
      >
        <BarChart
          counts={stats.coverage.map((item) => ({
            value: item.field,
            count: item.count,
            label: `${item.share.toFixed(1)} %`,
          }))}
          total={stats.count}
          scale={stats.count}
        />
      </ChartCard>

      <section className="card">
        <h2>Anomaly counts</h2>
        <table className="table">
          <thead>
            <tr>
              <th scope="col">Anomaly</th>
              <th scope="col" className="num">
                Records
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map(([label, value]) => (
              <tr key={label}>
                <td>{label}</td>
                <td className="num">{typeof value === "number" ? fmt(value) : value}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="card">
        <h2>Records flagged as test publications</h2>
        <p className="caption">
          A narrow heuristic: the identifier, title or abstract is made only of test
          tokens, or the title starts with one. They are flagged and kept, never
          dropped — the consumer decides. Each one opens on its own page.
        </p>
        <ul className="chips">
          {quality.suspectedTests.map((identifier) => (
            <li key={identifier}>
              <Link to={recordPath(identifier)}>{identifier}</Link>
            </li>
          ))}
        </ul>
      </section>

      <section className="card">
        <h2>What never reached this catalogue</h2>
        <p className="caption">
          Measured on the full run of 2026-09-20, against the live service — these
          counts come from the harvest, not from the catalogue below.
        </p>
        <p className="funnel">
          <span>
            <strong>336</strong> published
          </span>
          <span aria-hidden="true">→</span>
          <span>
            <strong>333</strong> harvested
          </span>
          <span aria-hidden="true">→</span>
          <span>
            <strong>326</strong> in the pivot catalogue
          </span>
        </p>
        <ul className="prose">
          <li>
            <strong>3 records cannot be served as ISO 19115-3.</strong> The service
            fails to transform them with <code>mdb-full.xsl</code>:{" "}
            <code>IGNF_BD-TRANSPORTS-EXCEPTIONNELS</code>,{" "}
            <code>MTECT_CORINE-LAND-COVER</code> and{" "}
            <code>fr-662043116-7D3DC709-E1EB-470B-9FD0-8ABF8AAFD8E4</code>. They exist
            in the older <code>gmd</code> schema.
          </li>
          <li>
            <strong>7 records are published with no identification block at all</strong>
            , so they carry neither title nor abstract and are counted as parse failures
            rather than written as empty records.
          </li>
          <li>
            <strong>No record says which service serves which dataset.</strong>{" "}
            <code>srv:operatesOn</code> and <code>mdb:parentMetadata</code> appear zero
            times, so the relation cannot be published without guessing it.
          </li>
        </ul>
      </section>
    </>
  );
}
