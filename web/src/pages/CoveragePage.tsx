// Author: Claude (Anthropic) — this file is AI generated, see ../../../docs/init.md.

/* The one page that is not about the catalogue alone. Every other view answers
   "what does the catalogue say?"; this one puts the catalogue next to what three
   services say they serve, and reports the difference in both directions.

   Nothing is derived here: `gpf_catalogue/coverage.py` did the matching and
   `coverage.json` carries the result, lists included. The page counts array
   lengths and draws bars. */

import { useState, type JSX } from "react";
import { Link } from "react-router";

import { useCatalogue } from "../catalogue";
import { BarChart, ChartCard } from "../components/Chart";
import { fmt, recordPath, share } from "../format";
import { usePageTitle } from "../title";
import type { ServiceCoverage } from "../types";

/** Rows of a long list shown before the "show all" button. */
const TOP_N = 25;

/** The share as a number, for a bar whose axis is a full 100 rather than a count. */
function percent(count: number, total: number): number {
  return total ? Math.round((1000 * count) / total) / 10 : 0;
}

/** A list that opens rather than one that scrolls: 387 rows is a page of its own. */
function Rows({
  children,
  total,
  noun,
}: {
  children: JSX.Element[];
  total: number;
  noun: string;
}): JSX.Element {
  const [expanded, setExpanded] = useState(false);
  const limited = total > TOP_N;

  return (
    <>
      <div className="table-wrap">
        <table className="table">
          <tbody>{limited && !expanded ? children.slice(0, TOP_N) : children}</tbody>
        </table>
      </div>
      {limited ? (
        <button
          type="button"
          className="ghost chart-more"
          onClick={() => setExpanded(!expanded)}
        >
          {expanded ? "Show fewer" : `Show all ${fmt(total)} ${noun}`}
        </button>
      ) : null}
    </>
  );
}

function Service({ service }: { service: ServiceCoverage }): JSX.Element {
  const uncovered = service.published - service.covered;

  return (
    <section className="card">
      <h2>
        {service.service.toUpperCase()}{" "}
        <span className="coverage-endpoint">{service.endpoint}</span>
      </h2>
      <p className="caption">
        The service publishes {fmt(service.published)} {service.label}.{" "}
        {fmt(service.covered)} of them — {share(service.covered, service.published)} —
        are described by one of the {fmt(service.records)} records citing this
        service.
      </p>

      {/* `total` is deliberately not passed: the chart would then read the share
          as "of the catalogue", and this bar is a share of what the *service*
          publishes. The share is on the bar end instead. */}
      <BarChart
        counts={[
          {
            value: "Described by a record",
            count: service.covered,
            label: `${fmt(service.covered)} — ${share(service.covered, service.published)}`,
          },
          {
            value: "Described by none",
            count: uncovered,
            label: `${fmt(uncovered)} — ${share(uncovered, service.published)}`,
            aside: true,
          },
        ]}
        scale={service.published}
        unit={service.label}
      />

      <table className="table">
        <tbody>
          <tr>
            <td>Served by the service</td>
            <td className="num">{fmt(service.published)}</td>
          </tr>
          <tr>
            <td>Cited by the catalogue</td>
            <td className="num">{fmt(service.claimed)}</td>
          </tr>
          <tr>
            <td>Links of this type, in the catalogue</td>
            <td className="num">{fmt(service.links)}</td>
          </tr>
          <tr>
            <td>…of which nothing can be matched on</td>
            <td className="num">{fmt(service.linksWithoutKey)}</td>
          </tr>
        </tbody>
      </table>

      {uncovered ? (
        <>
          <h3 className="section-title">
            {fmt(uncovered)} {service.label} no record describes
          </h3>
          <p className="caption">
            In the order the service lists them — a capabilities groups related
            entries, and that grouping is a reading aid it already produced. This is
            the actionable half of the page.
          </p>
          <Rows total={service.uncovered.length} noun={service.label}>
            {service.uncovered.map((resource) => (
              <tr key={resource.key}>
                <td className="coverage-key">{resource.key}</td>
                <td>{resource.title ?? ""}</td>
              </tr>
            ))}
          </Rows>
        </>
      ) : null}

      {service.unknown.length ? (
        <>
          <h3 className="section-title">
            {fmt(service.unknown.length)} cited by a record, served by no one
          </h3>
          <p className="caption">
            The record names it, the service does not publish it: a withdrawn layer,
            a record that was not updated, or an endpoint the public capabilities
            does not cover — <code>data.geopf.fr/private/wfs</code> is one. Each row
            names the records that made the claim.
          </p>
          <Rows total={service.unknown.length} noun="claims">
            {service.unknown.map((claim) => (
              <tr key={claim.key}>
                <td className="coverage-key">{claim.key}</td>
                <td>
                  <ul className="chips">
                    {claim.records.map((identifier) => (
                      <li key={identifier}>
                        <Link to={recordPath(identifier)}>{identifier}</Link>
                      </li>
                    ))}
                    {claim.citing > claim.records.length ? (
                      <li className="muted">
                        and {fmt(claim.citing - claim.records.length)} more
                      </li>
                    ) : null}
                  </ul>
                </td>
              </tr>
            ))}
          </Rows>
        </>
      ) : null}
    </section>
  );
}

export function CoveragePage(): JSX.Element {
  const { coverage } = useCatalogue();
  usePageTitle("Coverage");

  return (
    <>
      <p className="lead">
        How much of what the Géoplateforme <em>serves</em> the catalogue{" "}
        <em>describes</em>. Every other page on this site reads the catalogue alone;
        this one reads it against three services that publish their own inventory —
        the WFS, the WMTS and the download service.
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
                value: `${service.service} — ${fmt(service.covered)} of ${fmt(service.published)} ${service.label}`,
                // The bar is the percentage, pinned to a full 100, so its length
                // and its label are the same measurement.
                count: percent(service.covered, service.published),
                label: share(service.covered, service.published),
              }))}
              scale={100}
              unit="% described"
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
