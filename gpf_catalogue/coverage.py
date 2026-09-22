"""How much of what the Géoplateforme *serves* the catalogue *describes*.

`compute_coverage()` is a pure function over the pivot records and the mirrored
service inventories: no I/O, no network, like `parse_record()` and
`compute_stats()`. `scripts/coverage.py` is what reads the files and writes
`data/coverage.json`.

This is the one figure on the site that is not a property of the catalogue alone.
Every other aggregate answers *what does the catalogue say?*; this one answers
*what does it leave out?*, by putting two independent lists side by side:

- what a service publishes — 813 WFS feature types, 712 WMTS layers, 116 download
  resources, read from the services themselves by `gpf_catalogue.inventory`,
- what the catalogue claims — the `name` of every WFS and WMTS link, and the
  resource named by every download URL.

**The match is on the key, never on a title or a URL similarity.** `srv:operatesOn`
and `mdb:parentMetadata` appear zero times in the catalogue, so nothing states
which record describes which layer; the one thing that does tie them is that a WFS
link carries the `typeName` in `cit:name`, a WMTS link carries the layer
identifier, and a download link carries the resource in its URL path. Those are
the same strings the services publish, so comparing them compares two statements
about one thing. Matching a layer to a record by title similarity would invent the
relation the catalogue declined to publish, which is exactly what `docs/why.md`
refuses to do.

Three counts come out of it, and all three are worth reading:

- **covered**: the service publishes it and a record describes it,
- **uncovered**: the service publishes it and no record mentions it — a hole in
  the catalogue, and the actionable half of this page,
- **unknown**: a record cites it and the service does not publish it — a stale
  record, a layer that was withdrawn, or a link to an endpoint the public
  capabilities does not cover, such as `data.geopf.fr/private/wfs`.
"""
# Author: Claude (Anthropic) — this file is AI generated, see docs/init.md.

import logging
from pathlib import Path

from pydantic import Field

from gpf_catalogue.inventory import PublishedResource, ServiceInventory, resource_key
from gpf_catalogue.model import BaseRecordModel, CatalogueRecord

logger = logging.getLogger(__name__)

#: Longest list of citing records kept beside an unknown claim. The point of the
#: list is to make a claim traceable to a record, and a claim cited by more than a
#: handful of records is a pattern, not a record to open.
MAX_CITING_RECORDS = 10


class UnknownClaim(BaseRecordModel):
    """A resource the catalogue cites and the service does not publish.

    Attributes:
        key: The key as the record spells it.
        records: Identifiers of the records citing it, so the claim can be traced
            back to what made it. Truncated at `MAX_CITING_RECORDS`.
        citing: How many records cite it, before that truncation.
    """

    key: str = Field(description="The key as the record spells it.")
    records: list[str] = Field(
        description=f"Records citing it, at most {MAX_CITING_RECORDS} of them."
    )
    citing: int = Field(description="How many records cite it.")


class ServiceCoverage(BaseRecordModel):
    """What one service serves, against what the catalogue describes of it."""

    service: str = Field(description="Short service name: `wfs`, `wmts`, `download`.")
    label: str = Field(description="What the resources of this service are called.")
    endpoint: str = Field(description="URL the inventory was read from.")

    published: int = Field(description="Resources the service says it serves.")
    covered: int = Field(
        description="Published resources at least one record describes."
    )
    uncovered: list[PublishedResource] = Field(
        description=(
            "Published resources no record mentions, in the order the service "
            "listed them. This is the actionable half of the page."
        )
    )

    claimed: int = Field(
        description="Distinct keys the catalogue cites for this service."
    )
    unknown: list[UnknownClaim] = Field(
        description=(
            "Keys the catalogue cites that the service does not publish: a "
            "withdrawn layer, a stale record, or an endpoint outside the public "
            "capabilities."
        )
    )

    links: int = Field(description="Links of this type in the pivot catalogue.")
    links_without_key: int = Field(
        description=(
            "Links of this type carrying nothing to match on — a WFS or WMTS link "
            "with no `cit:name`, a download link pointing straight at a file."
        )
    )
    records: int = Field(
        description="Records describing at least one resource this service serves."
    )


class CatalogueCoverage(BaseRecordModel):
    """The coverage of every service the inventory of which was harvested.

    Carries no timestamp, like `catalogue.json` and `stats.json`: two runs over the
    same mirror produce the same bytes.
    """

    records: int = Field(description="Records the coverage was computed over.")
    services: list[ServiceCoverage] = Field(
        description="One entry per service, in the order the inventories were given."
    )


def claimed_keys(
    records: list[CatalogueRecord], service: str
) -> dict[str, list[str]]:
    """Return what the catalogue claims of one service, and who claims it.

    Where the key is read depends on the service, and each rule reads the field the
    catalogue actually fills:

    - `wfs` and `wmts`: `cit:name`, which carries the `typeName` for the WFS
      (`BDTOPO_V3:batiment`) and the layer identifier for the WMTS. 656 of the 657
      WFS links and 351 of the 353 WMTS links carry one.
    - `download`: the resource named by the URL path, because a download link
      carries a URL and not a layer. Only `/telechargement/resource/{key}` is a
      claim — a link straight to a `.7z` inside a delivery names no resource.

    Args:
        records: The pivot records.
        service: `wfs`, `wmts` or `download`.

    Returns:
        Key to the identifiers of the records citing it, sorted and deduplicated.

    Raises:
        ValueError: If `service` is not one of the three known ones.
    """
    return _scan(records, service)[0]


def _scan(
    records: list[CatalogueRecord], service: str
) -> tuple[dict[str, list[str]], int, int]:
    """Read the claims of one service in a single pass over the links.

    Returns:
        The claims, the number of links of that type, and how many of them carry
        nothing to match on.

    Raises:
        ValueError: If `service` is not one of the three known ones.
    """
    if service not in {"wfs", "wmts", "download"}:
        raise ValueError(f"unknown service: {service!r}")

    claims: dict[str, set[str]] = {}
    links = 0
    without_key = 0
    for record in records:
        for link in record.links:
            if link.type.value != service:
                continue
            links += 1
            key = resource_key(link.url) if service == "download" else _name(link.name)
            if not key:
                without_key += 1
                continue
            claims.setdefault(key, set()).add(record.file_identifier)
    return (
        {key: sorted(citing) for key, citing in claims.items()},
        links,
        without_key,
    )


def compute_coverage(
    records: list[CatalogueRecord], inventories: list[ServiceInventory]
) -> CatalogueCoverage:
    """Compare the pivot catalogue against what the services say they serve.

    Pure: no I/O, no network, no mutation of the records.

    Args:
        records: The pivot records.
        inventories: The service inventories to compare them against. A service
            whose inventory could not be harvested is simply absent, so the page
            reports two services rather than a wrong third.

    Returns:
        One coverage entry per inventory.
    """
    return CatalogueCoverage(
        records=len(records),
        services=[_service(records, inventory) for inventory in inventories],
    )


def _service(
    records: list[CatalogueRecord], inventory: ServiceInventory
) -> ServiceCoverage:
    """Compare the catalogue against one service inventory."""
    service = inventory.service
    published = inventory.keys
    claims, links, links_without_key = _scan(records, service)

    covered = [key for key in claims if key in published]
    # In the order the service listed them, not sorted: a capabilities groups
    # related layers together, and that grouping is a reading aid the service
    # already produced.
    uncovered = [
        resource for resource in inventory.resources if resource.key not in claims
    ]
    unknown = sorted(
        (
            UnknownClaim(
                key=key,
                records=citing[:MAX_CITING_RECORDS],
                citing=len(citing),
            )
            for key, citing in claims.items()
            if key not in published
        ),
        key=lambda claim: claim.key,
    )

    describing = {identifier for key in covered for identifier in claims[key]}

    coverage = ServiceCoverage(
        service=service,
        label=_LABELS.get(service, service),
        endpoint=inventory.endpoint,
        published=len(published),
        covered=len(covered),
        uncovered=uncovered,
        claimed=len(claims),
        unknown=unknown,
        links=links,
        links_without_key=links_without_key,
        records=len(describing),
    )
    logger.info(
        "%s: %d/%d covered, %d unknown claims",
        service,
        coverage.covered,
        coverage.published,
        len(unknown),
    )
    return coverage


#: What the resources of each service are called, so a page never says "resources"
#: where the service says "feature types".
_LABELS = {
    "wfs": "feature types",
    "wmts": "layers",
    "download": "resources",
}


def _name(value: str | None) -> str | None:
    """Return a link name usable as a key, or `None` when there is nothing to match."""
    return value.strip() or None if value else None


def coverage_markdown(coverage: CatalogueCoverage) -> str:
    """Render the service coverage as a markdown table.

    The documentation quotes these figures, and a quoted figure typed by hand is a
    figure that drifts. This is what `scripts/coverage.py --format markdown`
    prints, to be pasted into `docs/overview.md`.

    Args:
        coverage: The coverage to describe.

    Returns:
        A markdown table, newline terminated.
    """
    lines = [
        f"Measured over the {coverage.records} records of the pivot catalogue.",
        "",
        "| Service | Published | Described | Coverage | Not described | Cited, not served |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for service in coverage.services:
        share = (
            f"{100 * service.covered / service.published:.1f} %"
            if service.published
            else "—"
        )
        lines.append(
            f"| `{service.service}` ({service.label}) | {service.published} "
            f"| {service.covered} | {share} | {len(service.uncovered)} "
            f"| {len(service.unknown)} |"
        )
    return "\n".join(lines) + "\n"


def write_coverage(coverage: CatalogueCoverage, path: Path) -> None:
    """Write the coverage as a JSON document.

    Like `catalogue.json` and `stats.json`, the output carries no timestamp: two
    runs over the same mirror produce the same bytes.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        coverage.model_dump_json(by_alias=True, indent=2) + "\n", encoding="utf-8"
    )
    logger.info("wrote %s (%d services)", path, len(coverage.services))
