#!/usr/bin/env python3
"""Export the JSON schema of the pivot model to docs/pivot-schema.json.

The schema is the contract consumers rely on, so it is versioned and regenerated
whenever the model changes.

Example:
  uv run scripts/export_schema.py
"""

import argparse
import json
from pathlib import Path

from gpf_catalogue.cli import configure_logging
from gpf_catalogue.model import CatalogueRecord
from gpf_catalogue.storage import ROOT_DIR

DEFAULT_OUTPUT = ROOT_DIR / "docs" / "pivot-schema.json"


def main() -> int:
    """Write the JSON schema of `CatalogueRecord`."""
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="destination file (default: %(default)s)",
    )
    args = parser.parse_args()
    configure_logging()

    schema = CatalogueRecord.model_json_schema(by_alias=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(schema, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"schema written to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
