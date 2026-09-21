#!/usr/bin/env python3
"""Build the static overview site into site/, from data/catalogue.json.

The front end is built separately, by Vite: run `npm ci && npm run build` in web/
first, which writes web/dist. This script copies that output next to the JSON
documents it reads. The service coverage is included when data/services holds the
inventories mirrored by scripts/harvest_services.py, and left out otherwise. No network access at runtime, and no CDN — React is bundled
into the copied assets.

A file:// open will not work, because the page fetches those documents, and plain
`python -m http.server` answers 404 on /records/{fileIdentifier}, which is a route
rather than a file. Use scripts/serve_site.py, which serves the entry document for
a route the way GitHub Pages serves the 404.html this build writes.

Examples:
  uv run scripts/build_site.py
  uv run scripts/build_site.py --output /tmp/site
  uv run scripts/serve_site.py
"""
# Author: Claude (Anthropic) — this file is AI generated, see docs/init.md.

import argparse
from pathlib import Path

from gpf_catalogue.cli import add_common_arguments, configure_logging
from gpf_catalogue.site import build_site
from gpf_catalogue.storage import DEFAULT_SERVICES_DIR


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
    parser.add_argument(
        "--assets",
        type=Path,
        help="built front end to copy (default: web/dist)",
    )
    parser.add_argument(
        "--services-dir",
        default=DEFAULT_SERVICES_DIR,
        type=Path,
        help="mirrored service inventories to measure the coverage against "
        "(default: %(default)s; holding none means no coverage.json)",
    )
    args = parser.parse_args()
    configure_logging(args.verbose)

    catalogue = args.catalogue or args.data_dir.parent / "catalogue.json"
    if not catalogue.is_file():
        raise SystemExit(f"{catalogue} not found, run 'uv run scripts/parse.py' first")

    report = build_site(
        catalogue,
        output_dir=args.output,
        assets_dir=args.assets,
        services_dir=args.services_dir,
    )

    print("=== Site summary ===")
    print(f"records     : {report.records}")
    print(f"coverage    : {', '.join(report.services) or 'not measured'}")
    print(f"files       : {len(report.files)}")
    for name in report.files:
        print(f"  - {name}")
    print(f"output      : {report.output}")
    print(f"serve with  : uv run scripts/serve_site.py --site {report.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
