// Author: Claude (Anthropic) — this file is AI generated, see ../../../docs/init.md.

/* The one page that is not about the catalogue alone. Every other view answers
   "what does the catalogue say?"; this one puts the catalogue next to what three
   services say they serve, and reports the difference in both directions.

   It carries the *answer* and nothing else: three bars, three tables of four
   counts, and the rule behind them. The lists — 298 feature types, 387 layers,
   137 claims — are what the answer is made of, not what it is, and each one has
   a route of its own at `/coverage/{service}`. Stacking all six on one page made
   it 900 rows long, so the figure a reader came for sat above a scroll nobody
   finished. */

import type { JSX } from "react";
import { Link } from "react-router";

import { useCatalogue } from "../catalogue";
import { BarChart, ChartCard } from "../components/Chart";
import {
  ServiceBar,
  ServiceCounts,
  percent,
  uncoveredCount,
} from "../components/Coverage";
import { coveragePath, fmt, share } from "../format";
import { usePageTitle } from "../title";
import type { ServiceCoverage } from "../types";

function Service({ service }: { service: ServiceCoverage }): JSX.Element {
  const uncovered = uncoveredCount(service);

  return (
    <section className="card">
      <h2>
        <Link to={coveragePath(service.service)}>{service.service.toUpperCase()}</Link>{" "}
        <span className="coverage-endpoint">{service.endpoint}</span>
      </h2>
      <p className="caption">
        The service publishes {fmt(service.published)} {service.label}.{" "}
        {fmt(service.covered)} of them — {share(service.covered, service.published)} —
        are described by one of the {fmt(service.records)} records citing this
        service.
      </p>

      <ServiceBar service={service} />
      <ServiceCounts service={service} />

      <p className="coverage-more">
        <Link to={coveragePath(service.service)}>
          {uncovered
            ? `The ${fmt(uncovered)} ${service.label} no record describes`
            : `Everything this service serves is described`}
          {service.unknown.length
            ? `, and the ${fmt(service.unknown.length)} cited by a record and served by no one`
            : ""}
        </Link>
      </p>
    </section>
  );
}

/* The bar of a service reads as a sentence, and the same string is the key the
   chart links on: deriving the service back out of a formatted label would break
   the day the wording changes. */
function barLabel(service: ServiceCoverage): string {
  return `${service.service} — ${fmt(service.covered)} of ${fmt(service.published)} ${service.label}`;
}

export function CoveragePage(): JSX.Element {
  const { coverage } = useCatalogue();
  usePageTitle("Coverage");

  const pathOf = new Map(
    (coverage?.services ?? []).map((service) => [
      barLabel(service),
      coveragePath(service.service),
    ]),
  );

  return (
    <>
      <p className="lead">
        How much of what the Géoplateforme <em>serves</em> the catalogue{" "}
        <em>describes</em>. Every other page on this site reads the catalogue alone;
        this one reads it against three services that publish their own inventory —
        the WFS, the WMTS and the download service. Each one opens on a page listing
        what it is missing.
      </p>

      {coverage ? (
        <>
          <ChartCard
            title="Described, per service"
            wide
            caption="The share of what each service serves that at least one metadata record describes. The three services publish different numbers of things, so the bars plot the share and not the count — 515 of 813 is a longer bar than 325 of 712, which 515 against 325 would have drawn the other way round."
          >
            <BarChart
              counts={coverage.services.map((service) => ({
                value: barLabel(service),
                // The bar is the percentage, pinned to a full 100, so its length
                // and its label are the same measurement.
                count: percent(service.covered, service.published),
                label: share(service.covered, service.published),
              }))}
              scale={100}
              unit="% described"
              linkTo={(value) => pathOf.get(value) ?? "/coverage"}
            />
          </ChartCard>

          {coverage.services.map((service) => (
            <Service key={service.service} service={service} />
          ))}

          <section className="card">
            <h2>How a layer is matched to a record</h2>
            <p className="caption">
              Nothing in the catalogue states which record describes which layer:{" "}
              <code>srv:operatesOn</code> and <code>mdb:parentMetadata</code> appear
              zero times. So the match is on the one string the two sides share, and
              never on a similar title.
            </p>
            <ul className="prose">
              <li>
                <strong>WFS</strong> — the link name is the <code>typeName</code>,{" "}
                <code>BDTOPO_V3:batiment</code>, which is what{" "}
                <code>wfs:FeatureType/wfs:Name</code> publishes.
              </li>
              <li>
                <strong>WMTS</strong> — the link name is the layer identifier,{" "}
                <code>ORTHOIMAGERY.ORTHOPHOTOS</code>, which is the{" "}
                <code>ows:Identifier</code> of a <code>wmts:Layer</code>.
              </li>
              <li>
                <strong>Download</strong> — a download link carries a URL and not a
                layer, so the resource is read from its path:{" "}
                <code>/telechargement/resource/ADMIN-EXPRESS</code>. A link straight
                at a file inside a delivery names no resource and is counted as
                unmatchable rather than as a wrong claim.
              </li>
            </ul>
            <p className="prose-p">
              A record and a layer sharing a theme but no key are reported as two
              separate gaps. Pairing them by title similarity would invent the
              relation the catalogue declined to publish.
            </p>
          </section>
        </>
      ) : (
        <p className="notice">
          This build carries no <code>coverage.json</code>. Measuring the coverage
          needs the inventories of three services other than the CSW: run{" "}
          <code>uv run scripts/harvest_services.py</code>, then{" "}
          <code>uv run scripts/build_site.py</code>.
        </p>
      )}
    </>
  );
}
