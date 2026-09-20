#!/usr/bin/env python3
"""Build the static overview site into site/, from data/catalogue.json.

No network access, no runtime dependency: the result is plain HTML, CSS and
JavaScript next to the two JSON documents they read. Serve it with any static file
server; a file:// open will not work, because the page fetches those documents.

Examples:
  uv run scripts/build_site.py
  uv run scripts/build_site.py --output /tmp/site
  uv run python -m http.server -d site 8000
"""
# Author: Claude (Anthropic) — this file is AI generated, see docs/init.md.

import argparse
from pathlib import Path

from gpf_catalogue.cli import add_common_arguments, configure_logging
from gpf_catalogue.site import build_site


def main() -> int:
    """Build the site and report what was written.

    Returns:
        0 once the site is written.
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
        help="where to write the site (default: site/ at the repository root)",
    )
    args = parser.parse_args()
    configure_logging(args.verbose)

    catalogue = args.catalogue or args.data_dir.parent / "catalogue.json"
    if not catalogue.is_file():
        raise SystemExit(f"{catalogue} not found, run 'uv run scripts/parse.py' first")

    report = build_site(catalogue, output_dir=args.output)

    print("=== Site summary ===")
    print(f"records     : {report.records}")
    print(f"files       : {len(report.files)}")
    for name in report.files:
        print(f"  - {name}")
    print(f"output      : {report.output}")
    print(f"serve with  : uv run python -m http.server -d {report.output} 8000")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
