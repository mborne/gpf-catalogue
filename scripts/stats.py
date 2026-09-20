#!/usr/bin/env python3
"""Aggregate the pivot catalogue into data/stats.json, and report what it holds.

Reads the data/catalogue.json produced by scripts/parse.py. No network access.

Use --format markdown to print the coverage table quoted by docs/model.md, so the
figures in the documentation are measured rather than remembered.

Examples:
  uv run scripts/stats.py
  uv run scripts/stats.py --format markdown
  uv run scripts/stats.py --data-dir /tmp/csw --verbose
"""
# Author: Claude (Anthropic) — this file is AI generated, see docs/init.md.

import argparse
from pathlib import Path

from gpf_catalogue.cli import add_common_arguments, configure_logging
from gpf_catalogue.stats import (
    compute_stats,
    coverage_markdown,
    load_records,
    write_stats,
)

#: How many values of a long tailed aggregate the text summary prints.
_TOP = 10


def main() -> int:
    """Aggregate the catalogue and print a summary.

    Returns:
        0 once the statistics are written.
    """
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    add_common_arguments(parser)
    parser.add_argument(
        "--catalogue",
        type=Path,
        help="aggregated catalogue to read (default: catalogue.json beside --data-dir)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="where to write the statistics (default: stats.json beside --data-dir)",
    )
    parser.add_argument(
        "--format",
        choices=("text", "markdown"),
        default="text",
        help="text prints a summary, markdown prints the coverage table "
        "(default: %(default)s)",
    )
    args = parser.parse_args()
    configure_logging(args.verbose)

    catalogue = args.catalogue or args.data_dir.parent / "catalogue.json"
    if not catalogue.is_file():
        raise SystemExit(f"{catalogue} not found, run 'uv run scripts/parse.py' first")

    source, records = load_records(catalogue)
    stats = compute_stats(records, source=source or "https://data.geopf.fr/csw")

    output = args.output or args.data_dir.parent / "stats.json"
    write_stats(stats, output)

    if args.format == "markdown":
        # Only the table on stdout, so it can be piped into the documentation.
        print(coverage_markdown(stats), end="")
        return 0

    quality = stats.quality
    print("=== Stats summary ===")
    print(f"records     : {stats.count}")
    for item in stats.by_type:
        print(f"  {item.value:<10}: {item.count}")
    print(f"links       : {quality.links_total} ({quality.links_distinct_urls} distinct URLs)")

    _print_counts("topic categories", stats.by_topic_category)
    _print_counts("INSPIRE themes", stats.by_inspire_theme)
    _print_counts("publishers (email domain)", stats.by_publisher)
    _print_counts("licence families", stats.by_licence_family)
    _print_counts("records by link type", stats.records_by_link_type)

    print("field coverage:")
    for item in stats.coverage:
        print(f"  {item.field:<18}: {item.count:>4} ({item.share:5.1f} %)")

    print("quality:")
    print(f"  no title          : {quality.missing_title}")
    print(f"  no abstract       : {quality.missing_abstract}")
    print(f"  no access link    : {quality.records_without_links}")
    print(f"  links unlabelled  : {quality.links_without_name}")
    print(f"  links no descr.   : {quality.links_without_description}")
    print(f"  undeclared licence: {quality.undeclared_licence}")
    print(f"  undeclared access : {quality.undeclared_access_constraint}")
    print(f"  producer spellings: {quality.distinct_producers}")
    print(f"  suspected tests   : {len(quality.suspected_tests)}")
    for identifier in quality.suspected_tests:
        print(f"    - {identifier}")
    print(f"output      : {output}")
    return 0


def _print_counts(label: str, counts: list) -> None:
    """Print the most frequent values of one aggregate, and how many are left."""
    print(f"{label}: {len(counts)} distinct")
    for item in counts[:_TOP]:
        print(f"  {item.value:<40}: {item.count:>4}")
    if len(counts) > _TOP:
        print(f"  ... and {len(counts) - _TOP} more")


if __name__ == "__main__":
    raise SystemExit(main())
