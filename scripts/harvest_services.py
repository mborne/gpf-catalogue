#!/usr/bin/env python3
"""Mirror what the Géoplateforme services say they serve, into data/services/.

Three services publish their own inventory, and putting it beside the catalogue is
what says how much of the Géoplateforme the metadata actually describes:

  wfs       https://data.geopf.fr/wfs?REQUEST=GetCapabilities        (5.2 MB)
  wmts      https://data.geopf.fr/wmts?REQUEST=GetCapabilities       (2.9 MB)
  download  https://data.geopf.fr/telechargement/capabilities        (Atom, paginated)

An inventory already on disk is skipped, so an interrupted run can be restarted and
a coverage run costs nothing. One unreachable service does not stop the other two.

Examples:
  uv run scripts/harvest_services.py                 # the three inventories
  uv run scripts/harvest_services.py --only wmts --force
  uv run scripts/coverage.py                         # then compare them
"""
# Author: Claude (Anthropic) — this file is AI generated, see docs/init.md.

import argparse
from pathlib import Path

from gpf_catalogue.cli import add_common_arguments, configure_logging
from gpf_catalogue.harvest import harvest_services
from gpf_catalogue.services import SERVICES
from gpf_catalogue.storage import DEFAULT_SERVICES_DIR


def main() -> int:
    """Mirror the service inventories and report what happened.

    Returns:
        0 if every requested inventory is on disk, 1 if at least one failed.
    """
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    add_common_arguments(parser)
    parser.add_argument(
        "--services-dir",
        default=DEFAULT_SERVICES_DIR,
        type=Path,
        help="where to mirror the inventories (default: %(default)s)",
    )
    parser.add_argument(
        "--only",
        action="append",
        choices=sorted(SERVICES),
        metavar="SERVICE",
        help=f"harvest only this service ({', '.join(sorted(SERVICES))}), repeatable",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="fetch inventories already on disk again",
    )
    args = parser.parse_args()
    configure_logging(args.verbose)

    report = harvest_services(
        services_dir=args.services_dir, only=args.only, force=args.force
    )

    print("=== Service harvest summary ===")
    for name, pages in report.fetched.items():
        print(f"fetched    : {name} ({pages} page(s))")
    for name in report.skipped:
        print(f"skipped    : {name}, already on disk (use --force to refresh)")
    for name in report.failed:
        print(f"failed     : {name}")
    print(f"output     : {args.services_dir}")
    return 1 if report.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
