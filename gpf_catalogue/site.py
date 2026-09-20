"""Assembly of the static overview site.

The site is three files of vanilla HTML, CSS and JavaScript — `gpf_catalogue/web/` —
copied next to the two JSON documents they read. There is no template engine, no
bundler and no runtime dependency: building the site is a copy plus an aggregation,
and serving it is any static file server.

The catalogue is **copied** into the output rather than referenced through a relative
path out of it, so that the directory can be moved, zipped or published on its own
(ROADMAP phase 5).
"""
# Author: Claude (Anthropic) — this file is AI generated, see docs/init.md.

import logging
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from gpf_catalogue.stats import compute_stats, load_records, write_stats
from gpf_catalogue.storage import ROOT_DIR

logger = logging.getLogger(__name__)

#: The page and its assets, versioned with the package.
WEB_DIR = Path(__file__).resolve().parent / "web"

#: Default destination of the built site. Rebuildable, and gitignored like `data/`.
DEFAULT_SITE_DIR = ROOT_DIR / "site"

#: Name the catalogue takes inside the site, whatever it is called outside.
CATALOGUE_NAME = "catalogue.json"

#: Name the aggregates take inside the site.
STATS_NAME = "stats.json"


@dataclass
class SiteReport:
    """Outcome of a site build.

    Attributes:
        records: Number of records the site describes.
        output: Directory the site was written to.
        files: Names of the files written, in the order they were written.
    """

    records: int = 0
    output: Path = ROOT_DIR
    files: list[str] = field(default_factory=list)


def build_site(catalogue_path: Path, output_dir: Path | None = None) -> SiteReport:
    """Build the static overview site from an aggregated catalogue.

    Args:
        catalogue_path: The `catalogue.json` written by `scripts/parse.py`.
        output_dir: Where to write the site. Defaults to `site/` at the repository
            root.

    Returns:
        A report of what was written.

    Raises:
        FileNotFoundError: If the catalogue does not exist.
        ValueError: If it is not an aggregated catalogue.
    """
    if not catalogue_path.is_file():
        raise FileNotFoundError(catalogue_path)

    target = output_dir if output_dir is not None else DEFAULT_SITE_DIR
    target.mkdir(parents=True, exist_ok=True)

    source, records = load_records(catalogue_path)
    stats = compute_stats(records, source=source or "https://data.geopf.fr/csw")

    report = SiteReport(records=len(records), output=target)
    for asset in sorted(WEB_DIR.iterdir()):
        if not asset.is_file():
            continue
        # copyfile, not copy2: the site carries no modification time either, so two
        # builds of the same catalogue differ in nothing at all.
        shutil.copyfile(asset, target / asset.name)
        report.files.append(asset.name)
        logger.debug("copied %s", asset.name)

    shutil.copyfile(catalogue_path, target / CATALOGUE_NAME)
    report.files.append(CATALOGUE_NAME)
    write_stats(stats, target / STATS_NAME)
    report.files.append(STATS_NAME)

    logger.info("wrote %s (%d records)", target, len(records))
    return report
