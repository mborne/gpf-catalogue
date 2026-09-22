"""Mirroring of the Géoplateforme catalogue to `data/csw/{name}.xml`.

`harvest_services()` does the same for the three services that publish their own
inventory — what is *served*, against what the catalogue *describes*. It follows
the same rules: resumable, one failure reported rather than aborting the run.

The harvest is resumable: a record already on disk is skipped unless `force` is set,
so an interrupted run can simply be restarted. A record failing to download is
reported and does not abort the run.

The catalogue is always listed, even when only a few records are wanted, because
file names are computed from the whole set of identifiers (see `storage`).
"""
# Author: Claude (Anthropic) — this file is AI generated, see docs/init.md.

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

from gpf_catalogue.csw import CswClient
from gpf_catalogue.services import SERVICES, ServiceClient
from gpf_catalogue.storage import (
    build_filename_map,
    service_page_path,
    service_pages,
    xml_path,
)

logger = logging.getLogger(__name__)

#: Pause between two requests, to stay gentle with the service.
DEFAULT_DELAY = 0.2


@dataclass
class HarvestReport:
    """Outcome of a harvest run.

    Attributes:
        listed: Number of identifiers published by the service.
        selected: Number of identifiers this run was asked to harvest.
        downloaded: Number of records written to disk.
        skipped: Number of records already present on disk.
        failed: Identifiers of the records that could not be harvested.
        unknown: Requested identifiers absent from the catalogue.
    """

    listed: int = 0
    selected: int = 0
    downloaded: int = 0
    skipped: int = 0
    failed: list[str] = field(default_factory=list)
    unknown: list[str] = field(default_factory=list)


def harvest(
    data_dir: Path,
    client: CswClient | None = None,
    only: list[str] | None = None,
    limit: int | None = None,
    force: bool = False,
    delay: float = DEFAULT_DELAY,
) -> HarvestReport:
    """Download the catalogue records to `data_dir`.

    Args:
        data_dir: Destination directory, created if needed.
        client: CSW client to use, a default one is built when omitted.
        only: Restrict the harvest to these identifiers.
        limit: Stop after this number of records, useful for smoke runs.
        force: Download records again even when they are already on disk.
        delay: Pause in seconds between two downloads.

    Returns:
        A report of what was downloaded, skipped and failed.
    """
    client = client or CswClient()
    data_dir.mkdir(parents=True, exist_ok=True)

    identifiers = client.list_identifiers()
    stems = build_filename_map(identifiers)
    report = HarvestReport(listed=len(identifiers))

    if only:
        wanted = set(only)
        report.unknown = sorted(wanted - set(identifiers))
        for identifier in report.unknown:
            logger.error("unknown record identifier: %s", identifier)
        identifiers = [
            identifier for identifier in identifiers if identifier in wanted
        ]
    if limit is not None:
        identifiers = identifiers[:limit]
    report.selected = len(identifiers)

    for position, identifier in enumerate(identifiers, start=1):
        target = xml_path(data_dir, stems[identifier])
        if target.exists() and not force:
            logger.debug("skipping %s, already harvested", identifier)
            report.skipped += 1
            continue
        try:
            body = client.get_record(identifier)
        except Exception:
            # One broken record must not abort a run of several hundreds.
            logger.exception("failed to harvest %s", identifier)
            report.failed.append(identifier)
            continue
        target.write_bytes(body)
        report.downloaded += 1
        logger.info(
            "[%d/%d] %s -> %s (%d bytes)",
            position,
            report.selected,
            identifier,
            target.name,
            len(body),
        )
        if delay:
            time.sleep(delay)

    return report


@dataclass
class ServiceHarvestReport:
    """Outcome of a service inventory harvest.

    Attributes:
        fetched: Pages downloaded, per service.
        skipped: Services left untouched because they were already on disk.
        failed: Services whose inventory could not be fetched.
    """

    fetched: dict[str, int] = field(default_factory=dict)
    skipped: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)


def harvest_services(
    services_dir: Path,
    client: ServiceClient | None = None,
    only: list[str] | None = None,
    force: bool = False,
) -> ServiceHarvestReport:
    """Mirror the inventory of every service that publishes one.

    An inventory is fetched as a whole or not at all: unlike the 336 records of the
    catalogue, it is one document (or one feed of twelve pages) describing one
    service, and half of it describes nothing. So a service already on disk is
    skipped entirely unless `force` is set, and a partial fetch is discarded.

    Args:
        services_dir: Destination directory, created if needed.
        client: Client to use, a default one is built when omitted.
        only: Restrict the harvest to these service names.
        force: Fetch inventories again even when they are already on disk.

    Returns:
        A report of what was fetched, skipped and failed.

    Raises:
        ValueError: If `only` names a service that does not exist.
    """
    client = client or ServiceClient()
    services_dir.mkdir(parents=True, exist_ok=True)

    wanted = list(SERVICES)
    if only:
        unknown = sorted(set(only) - set(SERVICES))
        if unknown:
            raise ValueError(f"unknown service(s): {', '.join(unknown)}")
        wanted = [name for name in wanted if name in set(only)]

    report = ServiceHarvestReport()
    for name in wanted:
        existing = service_pages(services_dir, name)
        if existing and not force:
            logger.debug("skipping %s, already harvested", name)
            report.skipped.append(name)
            continue
        try:
            bodies = client.fetch(SERVICES[name])
        except Exception:
            # One unavailable service must not cost the other two: coverage is
            # reported per service, so two thirds of it is still worth publishing.
            logger.exception("failed to harvest the %s inventory", name)
            report.failed.append(name)
            continue

        # Written only once the whole inventory is in hand, and the pages of a
        # shorter run are removed: a feed that lost a page would otherwise keep
        # reporting the resources of the previous harvest.
        for page in existing:
            page.unlink()
        for number, body in enumerate(bodies, start=1):
            target = service_page_path(services_dir, name, number)
            target.write_bytes(body)
            logger.info("%s -> %s (%d bytes)", name, target.name, len(body))
        report.fetched[name] = len(bodies)

    return report
