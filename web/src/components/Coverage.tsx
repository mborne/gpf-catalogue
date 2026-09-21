// Author: Claude (Anthropic) — this file is AI generated, see ../../../docs/init.md.

/* The pieces `/coverage` and `/coverage/{service}` both draw: the summary of one
   service, and the long lists that are the reason the detail has a route of its
   own. Nothing here derives anything — `gpf_catalogue/coverage.py` did the
   matching and `coverage.json` carries the result, lists included. */

import { useState, type JSX } from "react";
import { Link } from "react-router";

import { fmt, recordPath, share } from "../format";
import type { ServiceCoverage } from "../types";
import { BarChart } from "./Chart";

/** The share as a number, for a bar whose axis is a full 100 rather than a count. */
export function percent(count: number, total: number): number {
  return total ? Math.round((1000 * count) / total) / 10 : 0;
}

/** How many of a service's resources no record describes. */
export function uncoveredCount(service: ServiceCoverage): number {
  return service.published - service.covered;
}

/**
 * Described against not described, for one service.
 *
 * `total` is deliberately not passed to the chart: it would read the share as "of
 * the catalogue", and this bar is a share of what the *service* publishes. The
 * share sits at the bar end instead.
 */
export function ServiceBar({ service }: { service: ServiceCoverage }): JSX.Element {
  const uncovered = uncoveredCount(service);
  return (
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
  );
}

/** The four counts that say what was compared, under the bar that shows the result. */
export function ServiceCounts({ service }: { service: ServiceCoverage }): JSX.Element {
  return (
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
  );
}

/** Rows of a long list shown before the "show all" button. */
const TOP_N = 50;

/** A list that opens rather than one that scrolls: 387 rows is a section of its own. */
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

/** What the service serves and no record describes. The actionable list. */
export function UncoveredList({ service }: { service: ServiceCoverage }): JSX.Element {
  return (
    <section className="card">
      <h2>
        {fmt(service.uncovered.length)} {service.label} no record describes
      </h2>
      <p className="caption">
        In the order the service lists them — a capabilities groups related entries,
        and that grouping is a reading aid it already produced.
      </p>
      <Rows total={service.uncovered.length} noun={service.label}>
        {service.uncovered.map((resource) => (
          <tr key={resource.key}>
            <td className="coverage-key">{resource.key}</td>
            <td>{resource.title ?? ""}</td>
          </tr>
        ))}
      </Rows>
    </section>
  );
}

/** What a record cites and the service does not serve, with who cited it. */
export function UnknownList({ service }: { service: ServiceCoverage }): JSX.Element {
  return (
    <section className="card">
      <h2>{fmt(service.unknown.length)} cited by a record, served by no one</h2>
      <p className="caption">
        The record names it, the service does not publish it: a withdrawn layer, a
        record that was not updated, or an endpoint the public capabilities does not
        cover — <code>data.geopf.fr/private/wfs</code> is one. Each row names the
        records that made the claim, so it can be opened.
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
    </section>
  );
}
