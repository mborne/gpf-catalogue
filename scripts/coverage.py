#!/usr/bin/env python3
"""Compare the pivot catalogue against what the services serve, into data/coverage.json.

Reads the data/catalogue.json produced by scripts/parse.py and the inventories
mirrored by scripts/harvest_services.py. No network access.

Answers the one question the catalogue cannot answer alone: of the feature types,
layers and download resources the Géoplateforme actually serves, how many does a
metadata record describe? A service whose inventory is missing is reported as such
and left out, rather than counted as uncovered.

Examples:
  uv run scripts/harvest_services.py && uv run scripts/coverage.py
  uv run scripts/coverage.py --format markdown
"""
# Author: Claude (Anthropic) — this file is AI generated, see docs/init.md.

import argparse
from pathlib import Path

from gpf_catalogue.cli import add_common_arguments, configure_logging
from gpf_catalogue.coverage import compute_coverage, coverage_markdown, write_coverage
from gpf_catalogue.inventory import read_inventories
from gpf_catalogue.stats import load_records
from gpf_catalogue.storage import DEFAULT_SERVICES_DIR

#: How many uncovered resources the text summary names before counting the rest.
_TOP = 5


def main() -> int:
    """Compute the coverage and print a summary.

    Returns:
        0 once the coverage is written, 1 if no inventory could be read at all.
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
        help="mirrored inventories to read (default: %(default)s)",
    )
    parser.add_argument(
        "--catalogue",
        type=Path,
        help="aggregated catalogue to read (default: catalogue.json beside --data-dir)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="where to write the coverage (default: coverage.json beside --data-dir)",
    )
    parser.add_argument(
        "--format",
        choices=("text", "markdown"),
        default="text",
        help="text prints a summary, markdown prints the table quoted by the docs "
        "(default: %(default)s)",
    )
    args = parser.parse_args()
    configure_logging(args.verbose)

    catalogue = args.catalogue or args.data_dir.parent / "catalogue.json"
    if not catalogue.is_file():
        raise SystemExit(f"{catalogue} not found, run 'uv run scripts/parse.py' first")

    _, records = load_records(catalogue)
    inventories, missing = read_inventories(args.services_dir)
    if not inventories:
        raise SystemExit(
            f"no inventory in {args.services_dir}, "
            "run 'uv run scripts/harvest_services.py' first"
        )

    coverage = compute_coverage(records, inventories)
    output = args.output or args.data_dir.parent / "coverage.json"
    write_coverage(coverage, output)

    if args.format == "markdown":
        # Only the table on stdout, so it can be piped into the documentation.
        print(coverage_markdown(coverage), end="")
        return 0

    print("=== Coverage summary ===")
    print(f"records     : {coverage.records}")
    for service in coverage.services:
        share = 100 * service.covered / service.published if service.published else 0.0
        print(f"{service.service}:")
        print(f"  published : {service.published} {service.label}")
        print(f"  covered   : {service.covered} ({share:.1f} %)")
        print(f"  uncovered : {len(service.uncovered)}")
        for resource in service.uncovered[:_TOP]:
            print(f"    - {resource.key}")
        if len(service.uncovered) > _TOP:
            print(f"    ... and {len(service.uncovered) - _TOP} more")
        print(f"  unknown   : {len(service.unknown)} keys cited by no published one")
        print(f"  links     : {service.links} ({service.links_without_key} unmatchable)")
        print(f"  records   : {service.records}")
    for name in missing:
        print(f"missing     : {name}, not harvested")
    print(f"output      : {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
