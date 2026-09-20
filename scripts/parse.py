#!/usr/bin/env python3
"""Convert harvested records into the pivot model, as data/csw/{fileIdentifier}.json.

Reads every data/csw/*.xml produced by scripts/harvest.py. No network access.

Examples:
  uv run scripts/parse.py
  uv run scripts/parse.py --data-dir /tmp/csw --verbose
"""

import argparse

from gpf_catalogue.cli import add_common_arguments, configure_logging
from gpf_catalogue.parse import parse_all


def main() -> int:
    """Convert the harvested records and report what happened.

    Returns:
        0 if every record was converted, 1 if at least one failed.
    """
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    add_common_arguments(parser)
    args = parser.parse_args()
    configure_logging(args.verbose)

    if not args.data_dir.is_dir():
        raise SystemExit(
            f"{args.data_dir} not found, run 'uv run scripts/harvest.py' first"
        )

    report = parse_all(args.data_dir)

    print("=== Parse summary ===")
    print(f"records     : {report.total}")
    print(f"written     : {report.written}")
    for resource_type, count in sorted(report.by_type.items()):
        print(f"  {resource_type:<10}: {count}")
    print(f"no title    : {report.missing_title}")
    print(f"no abstract : {report.missing_abstract}")
    print(f"failed      : {len(report.failed)}")
    for name, reason in report.failed:
        print(f"  - {name}: {reason}")
    print(f"output      : {args.data_dir}")
    return 1 if report.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
