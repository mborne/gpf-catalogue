"""Helpers shared by the command line scripts of `scripts/`."""
# Author: Claude (Anthropic) — this file is AI generated, see docs/init.md.

import argparse
import logging
from pathlib import Path

from gpf_catalogue.storage import DEFAULT_DATA_DIR


def add_common_arguments(parser: argparse.ArgumentParser) -> None:
    """Add the options every script of this project understands."""
    parser.add_argument(
        "--data-dir",
        default=DEFAULT_DATA_DIR,
        type=Path,
        help="directory holding the records (default: %(default)s)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="log debug messages",
    )


def configure_logging(verbose: bool = False) -> None:
    """Configure logging for a command line run.

    Logs go to stderr so that stdout stays usable for actual output.
    """
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
