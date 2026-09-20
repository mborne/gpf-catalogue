#!/usr/bin/env python3
"""Harvest the Géoplateforme catalogue into data/csw/{fileIdentifier}.xml.

Records already present are skipped, so an interrupted run can simply be restarted.

Examples:
  uv run scripts/harvest.py --limit 5          # smoke run on the first 5 records
  uv run scripts/harvest.py                    # mirror the whole catalogue
  uv run scripts/harvest.py --only IGNF_BD-TOPO --force
"""

import argparse

from gpf_catalogue.cli import add_common_arguments, configure_logging
from gpf_catalogue.csw import DEFAULT_CSW_URL, CswClient
from gpf_catalogue.harvest import DEFAULT_DELAY, harvest


def main() -> int:
    """Run the harvest and report what happened.

    Returns:
        0 if every requested record was harvested, 1 if at least one failed.
    """
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    add_common_arguments(parser)
    parser.add_argument(
        "--url", default=DEFAULT_CSW_URL, help="CSW endpoint (default: %(default)s)"
    )
    parser.add_argument(
        "--only",
        action="append",
        metavar="ID",
        help="harvest only this record, repeatable",
    )
    parser.add_argument(
        "--limit", type=int, help="stop after this number of records"
    )
    parser.add_argument(
        "--force", action="store_true", help="download records already on disk again"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=DEFAULT_DELAY,
        help="pause in seconds between two downloads (default: %(default)s)",
    )
    args = parser.parse_args()
    configure_logging(args.verbose)

    report = harvest(
        data_dir=args.data_dir,
        client=CswClient(url=args.url),
        only=args.only,
        limit=args.limit,
        force=args.force,
        delay=args.delay,
    )

    print("=== Harvest summary ===")
    print(f"listed     : {report.listed}")
    print(f"selected   : {report.selected}")
    print(f"downloaded : {report.downloaded}")
    print(f"skipped    : {report.skipped}")
    print(f"failed     : {len(report.failed)}")
    for identifier in report.failed:
        print(f"  - {identifier}")
    for identifier in report.unknown:
        print(f"  - unknown identifier: {identifier}")
    print(f"output     : {args.data_dir}")
    return 1 if report.failed or report.unknown else 0


if __name__ == "__main__":
    raise SystemExit(main())
