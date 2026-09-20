"""Assembly of the static overview site.

The site is a React application — `web/`, built by Vite — copied next to the two
JSON documents it reads. Building it is therefore two steps: `npm run build` in
`web/`, which produces `web/dist/`, then this module, which copies that output and
the data beside it. `web/dist/` is rebuildable and gitignored, like `data/` and
`site/`.

What the build still guarantees is what it guaranteed when the page was three
handwritten files: the result is **static**, self contained, and loads nothing from
a network at runtime. React is bundled into the copied assets, not fetched from a
CDN, and the only requests the page makes are for `catalogue.json` and
`stats.json` beside it.

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
        output: Directory the site was written to.
        files: Paths of the files written, relative to `output`, in the order they
            were written.
    """

    records: int = 0
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
) -> SiteReport:
    """Build the static overview site from an aggregated catalogue.

    Args:
        catalogue_path: The `catalogue.json` written by `scripts/parse.py`.
        output_dir: Where to write the site. Defaults to `site/` at the repository
            root.
        assets_dir: The built front end to copy. Defaults to `web/dist`.

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
    stats = compute_stats(records, source=source or "https://data.geopf.fr/csw")

    report = SiteReport(records=len(records), output=target)
    report.files.extend(_copy_assets(assets, target))

    shutil.copyfile(target / INDEX_NAME, target / NOT_FOUND_NAME)
    report.files.append(NOT_FOUND_NAME)

    shutil.copyfile(catalogue_path, target / CATALOGUE_NAME)
    report.files.append(CATALOGUE_NAME)
    write_stats(stats, target / STATS_NAME)
    report.files.append(STATS_NAME)

    logger.info("wrote %s (%d records)", target, len(records))
    return report
