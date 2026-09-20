#!/usr/bin/env python3
"""Serve the built site locally, with the routes the application declares.

`python -m http.server` answers 404 on /records/{fileIdentifier}, because that is a
route and not a file. This server answers it with the entry document, which is what
GitHub Pages does through the 404.html the build writes.

Examples:
  uv run scripts/serve_site.py
  uv run scripts/serve_site.py --port 9000
  uv run scripts/serve_site.py --site /tmp/site
"""
# Author: Claude (Anthropic) — this file is AI generated, see docs/init.md.

import argparse
from pathlib import Path

from gpf_catalogue.cli import configure_logging
from gpf_catalogue.serve import serve
from gpf_catalogue.site import DEFAULT_SITE_DIR


def main() -> int:
    """Serve the site until interrupted.

    Returns:
        0 once the server has stopped.
    """
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="log debug messages",
    )
    parser.add_argument(
        "--site",
        type=Path,
        default=DEFAULT_SITE_DIR,
        help="directory to serve (default: site/ at the repository root)",
    )
    parser.add_argument("--port", type=int, default=8000, help="port (default: 8000)")
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="interface to bind (default: 127.0.0.1)",
    )
    args = parser.parse_args()
    configure_logging(args.verbose)

    if not (args.site / "index.html").is_file():
        raise SystemExit(
            f"{args.site} holds no built site, run 'uv run scripts/build_site.py' first"
        )

    try:
        serve(args.site, port=args.port, host=args.host)
    except OSError as error:
        # Almost always a port already taken by something else. A traceback is
        # not what a preview command owes anyone.
        raise SystemExit(
            f"cannot serve on {args.host}:{args.port}: "
            f"{error.strerror or error} — try another --port"
        ) from error
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
