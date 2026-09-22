// Author: Claude (Anthropic) — this file is AI generated, see ../../../docs/init.md.

import type { JSX } from "react";
import { Link, useParams } from "react-router";

import { useCatalogue } from "../catalogue";
import {
  ServiceBar,
  ServiceCounts,
  UncoveredList,
  UnknownList,
  uncoveredCount,
} from "../components/Coverage";
import { fmt, share } from "../format";
import { usePageTitle } from "../title";

/**
 * What one service serves and the catalogue does not describe, at
 * `/coverage/{service}`.
 *
 * The lists live here rather than on `/coverage` because they are long — 298
 * feature types, 387 layers, 137 claims — and because each is a working list: a
 * link to *the WMTS layers nobody documented* is worth sending to someone, which
 * a section of a longer page could not be.
 */
export function CoverageServicePage(): JSX.Element {
  const { coverage } = useCatalogue();
  const { service: name } = useParams();
  const service = coverage?.services.find((item) => item.service === name) ?? null;
  usePageTitle(service ? `Coverage — ${service.service.toUpperCase()}` : "Coverage");

  if (!coverage) {
    return (
      <p className="notice">
        This build carries no <code>coverage.json</code>. Measuring the coverage needs
        the inventories of three services other than the CSW: run{" "}
        <code>uv run scripts/harvest_services.py</code>, then{" "}
        <code>uv run scripts/build_site.py</code>.
      </p>
    );
  }

  if (!service) {
    return (
      <section className="card">
        <h2>No coverage measured for this service</h2>
        <p className="caption">
          <code>{name}</code> is not one of the services this build compared the
          catalogue against. An inventory that could not be harvested is left out
          rather than reported as empty — an empty one would say the service serves
          nothing.
        </p>
        <p className="caption">
          <Link to="/coverage">Back to the coverage</Link>
        </p>
      </section>
    );
  }

  const uncovered = uncoveredCount(service);

  return (
    <>
      <p className="breadcrumb">
        <Link to="/coverage">Coverage</Link>
      </p>

      <section className="card">
        <h2>
          {service.service.toUpperCase()}{" "}
          <span className="coverage-endpoint">{service.endpoint}</span>
        </h2>
        <p className="caption">
          The service publishes {fmt(service.published)} {service.label}.{" "}
          {fmt(service.covered)} of them — {share(service.covered, service.published)}{" "}
          — are described by one of the {fmt(service.records)} records citing this
          service.
        </p>
        <ServiceBar service={service} />
        <ServiceCounts service={service} />
      </section>

      {uncovered ? <UncoveredList service={service} /> : null}
      {service.unknown.length ? <UnknownList service={service} /> : null}
    </>
  );
}
