"""Assembly of the static overview site.

The site is a React application — `web/`, built by Vite — copied next to the JSON
documents it reads. Building it is therefore two steps: `npm run build` in
`web/`, which produces `web/dist/`, then this module, which copies that output and
the data beside it. `web/dist/` is rebuildable and gitignored, like `data/` and
`site/`.

What the build still guarantees is what it guaranteed when the page was three
handwritten files: the result is **static**, self contained, and loads nothing from
a network at runtime. React is bundled into the copied assets, not fetched from a
CDN, and the only requests the page makes are for `catalogue.json`, `stats.json`
and `coverage.json` beside it.

`coverage.json` is the one document that may legitimately be absent: it needs the
inventories of three services other than the CSW (`scripts/harvest_services.py`),
and a run that never fetched them still produces a correct site — one that says the
coverage was not measured, rather than one reporting zero.

The catalogue is **copied** into the output rather than referenced through a
relative path out of it, so that the directory can be moved, zipped or published on
its own (ROADMAP phase 5).

`404.html` is a byte copy of `index.html`. The routes are real paths —
`/records/IGNF_BD-TOPO` — and a static host has no rewrite rule, so it answers an
unknown path with its 404 document. Serving the application as that document is
what makes a link to a record work on a cold load rather than only after a click.
"""
# Author: Claude (Anthropic) — this file is AI generated, see docs/init.md.

import logging
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from gpf_catalogue.coverage import compute_coverage, write_coverage
from gpf_catalogue.inventory import read_inventories
from gpf_catalogue.stats import compute_stats, load_records, write_stats
from gpf_catalogue.storage import ROOT_DIR

logger = logging.getLogger(__name__)

#: Source of the front end: a npm project, not a Python package resource.
WEB_DIR = ROOT_DIR / "web"

#: What `npm run build` writes, and what this module copies.
DEFAULT_ASSETS_DIR = WEB_DIR / "dist"

#: Default destination of the built site. Rebuildable, and gitignored like `data/`.
DEFAULT_SITE_DIR = ROOT_DIR / "site"

#: Name the catalogue takes inside the site, whatever it is called outside.
CATALOGUE_NAME = "catalogue.json"

#: Name the aggregates take inside the site.
STATS_NAME = "stats.json"

#: Name the service coverage takes inside the site, when it was measured at all.
COVERAGE_NAME = "coverage.json"

#: Entry document, and the one a static host serves for an unknown path.
INDEX_NAME = "index.html"

#: Copy of the entry document, so a deep link survives a cold load. See the module
#: docstring.
NOT_FOUND_NAME = "404.html"

#: Command to run when `web/dist` is missing, quoted in the error.
BUILD_COMMAND = "npm ci && npm run build"


@dataclass
class SiteReport:
    """Outcome of a site build.

    Attributes:
        records: Number of records the site describes.
        services: Names of the services whose coverage was measured, empty when no
            inventory was mirrored.
        output: Directory the site was written to.
        files: Paths of the files written, relative to `output`, in the order they
            were written.
    """

    records: int = 0
    services: list[str] = field(default_factory=list)
    output: Path = ROOT_DIR
    files: list[str] = field(default_factory=list)


def _copy_assets(assets_dir: Path, target: Path) -> list[str]:
    """Copy a built front end into the site, returning the relative paths written.

    Args:
        assets_dir: Directory produced by `npm run build`.
        target: Directory to copy it into; created if missing.

    Returns:
        The copied paths, relative to `target`, sorted.
    """
    # Asset file names carry a content hash, so a rebuild writes new ones and
    # leaves the previous ones behind. The directory is generated in full, so it
    # is cleared rather than merged into — otherwise every build of the week
    # accumulates in it.
    shutil.rmtree(target / "assets", ignore_errors=True)

    written: list[str] = []
    for source in sorted(assets_dir.rglob("*")):
        if not source.is_file():
            continue
        relative = source.relative_to(assets_dir)
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        # copyfile, not copy2: the site carries no modification time either, so two
        # builds of the same catalogue differ in nothing at all.
        shutil.copyfile(source, destination)
        written.append(relative.as_posix())
        logger.debug("copied %s", relative.as_posix())
    return written


def build_site(
    catalogue_path: Path,
    output_dir: Path | None = None,
    assets_dir: Path | None = None,
    services_dir: Path | None = None,
    built_at: str | None = None,
) -> SiteReport:
    """Build the static overview site from an aggregated catalogue.

    Args:
        catalogue_path: The `catalogue.json` written by `scripts/parse.py`.
        output_dir: Where to write the site. Defaults to `site/` at the repository
            root.
        assets_dir: The built front end to copy. Defaults to `web/dist`.
        services_dir: The mirrored service inventories to measure the coverage
            against. `None`, the default, measures nothing: the coverage is the
            one figure that depends on data outside `data/csw`, so the caller says
            where it is rather than the library reaching for it. A directory
            holding no inventory is the same as none at all.
        built_at: Date this build is running, ISO 8601, shown by the overview next
            to the record count. `None`, the default, shows nothing: the Pages
            workflow runs weekly, so a build with no date would otherwise let a
            week-old mirror look like it was just measured. Read from the clock
            by `scripts/build_site.py`, never by this function, so `build_site()`
            stays a function of its arguments — two calls with the same
            `built_at` write the same `stats.json`.

    Returns:
        A report of what was written.

    Raises:
        FileNotFoundError: If the catalogue does not exist, or if the front end has
            not been built.
        ValueError: If the catalogue is not an aggregated one.
    """
    if not catalogue_path.is_file():
        raise FileNotFoundError(catalogue_path)

    assets = assets_dir if assets_dir is not None else DEFAULT_ASSETS_DIR
    if not (assets / INDEX_NAME).is_file():
        raise FileNotFoundError(
            f"{assets / INDEX_NAME} not found: build the front end first, "
            f"with '{BUILD_COMMAND}' in {WEB_DIR}"
        )

    target = output_dir if output_dir is not None else DEFAULT_SITE_DIR
    target.mkdir(parents=True, exist_ok=True)

    source, records = load_records(catalogue_path)
    stats = compute_stats(
        records, source=source or "https://data.geopf.fr/csw", built_at=built_at
    )

    report = SiteReport(records=len(records), output=target)
    report.files.extend(_copy_assets(assets, target))

    shutil.copyfile(target / INDEX_NAME, target / NOT_FOUND_NAME)
    report.files.append(NOT_FOUND_NAME)

    shutil.copyfile(catalogue_path, target / CATALOGUE_NAME)
    report.files.append(CATALOGUE_NAME)
    write_stats(stats, target / STATS_NAME)
    report.files.append(STATS_NAME)

    # Left over from a previous build, the old coverage would be served beside a
    # catalogue it no longer describes. Removed before it is possibly rewritten.
    (target / COVERAGE_NAME).unlink(missing_ok=True)
    if services_dir is not None:
        inventories, missing = read_inventories(services_dir)
        if inventories:
            coverage = compute_coverage(records, inventories)
            write_coverage(coverage, target / COVERAGE_NAME)
            report.files.append(COVERAGE_NAME)
            report.services = [inventory.service for inventory in inventories]
        if missing:
            logger.warning(
                "no inventory for %s in %s: run scripts/harvest_services.py to "
                "measure the coverage of those services",
                ", ".join(missing),
                services_dir,
            )

    logger.info("wrote %s (%d records)", target, len(records))
    return report
