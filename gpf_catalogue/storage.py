"""Where harvested and converted records are stored on disk.

Layout, relative to the repository root:

- `data/csw/{name}.xml`: the raw ISO 19115-3 record, as sent by the service,
- `data/csw/{name}.json`: the same record in the pivot model.

`data/` is a rebuildable mirror of the Géoplateforme catalogue and is not versioned.

`{name}` is derived from the record identifier but is not always equal to it. Real
identifiers of the catalogue include spaces, accents, parentheses, a trailing `.xml`,
and pairs differing only by case (`id` and `ID`, `test` and `TEST`). The last case
would silently overwrite a record on a case insensitive file system, so file names
are computed for the catalogue as a whole, not one identifier at a time.
"""
# Author: Claude (Anthropic) — this file is AI generated, see docs/init.md.

import hashlib
import logging
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path
from urllib.parse import quote

logger = logging.getLogger(__name__)

#: Repository root, i.e. the parent of the `gpf_catalogue` package.
ROOT_DIR = Path(__file__).resolve().parent.parent

#: Default destination of harvested and converted records.
DEFAULT_DATA_DIR = ROOT_DIR / "data" / "csw"

#: Longest file name stem kept as is, before it is truncated and hashed.
MAX_STEM_LENGTH = 120


def safe_filename(identifier: str) -> str:
    """Return a file name stem for a record identifier, ignoring collisions.

    Identifiers come from a remote service and end up as paths, so they are never
    trusted as-is. Characters outside of `[A-Za-z0-9._~-]` are percent encoded,
    which is reversible, deterministic, and leaves most identifiers untouched.

    Args:
        identifier: The record identifier.

    Returns:
        A file name stem, without extension.

    Raises:
        ValueError: If the identifier is empty.
    """
    candidate = identifier.strip()
    if not candidate:
        raise ValueError("empty record identifier")

    stem = quote(candidate, safe=".-_~")
    if stem in {".", ".."} or stem.startswith("."):
        stem = f"_{stem}"
    if len(stem) > MAX_STEM_LENGTH:
        stem = f"{stem[:MAX_STEM_LENGTH]}-{_short_hash(candidate)}"
    return stem


def build_filename_map(identifiers: Iterable[str]) -> dict[str, str]:
    """Map every record identifier to a file name stem unique across the catalogue.

    Identifiers colliding once compared case insensitively all receive a short hash
    suffix, so that the name of a record never depends on the order records were
    harvested in.

    Args:
        identifiers: Every identifier of the catalogue.

    Returns:
        Identifier to file name stem, without extension.

    Raises:
        ValueError: If two distinct identifiers still yield the same stem.
    """
    unique = list(dict.fromkeys(identifiers))
    groups: dict[str, list[str]] = defaultdict(list)
    for identifier in unique:
        groups[safe_filename(identifier).casefold()].append(identifier)

    stems: dict[str, str] = {}
    for group in groups.values():
        if len(group) == 1:
            stems[group[0]] = safe_filename(group[0])
            continue
        logger.warning(
            "identifiers only differing by case, disambiguating with a hash: %s",
            ", ".join(repr(identifier) for identifier in group),
        )
        for identifier in group:
            stems[identifier] = f"{safe_filename(identifier)}-{_short_hash(identifier)}"

    taken = {stem.casefold() for stem in stems.values()}
    if len(taken) != len(stems):
        raise ValueError("unable to compute unique file names for the catalogue")
    return stems


def xml_path(data_dir: Path, stem: str) -> Path:
    """Return the path of the raw record for a given file name stem."""
    return _child(data_dir, f"{stem}.xml")


def json_path(data_dir: Path, stem: str) -> Path:
    """Return the path of the pivot record for a given file name stem."""
    return _child(data_dir, f"{stem}.json")


def stem_of(path: Path) -> str:
    """Return the file name stem of a record file.

    `Path.stem` and `Path.with_suffix()` are avoided on purpose: nine identifiers
    of the catalogue already end with `.xml` and one is `1.0`, which those would
    truncate.
    """
    return path.name.removesuffix(".xml").removesuffix(".json")


def _child(data_dir: Path, name: str) -> Path:
    """Return `data_dir / name`, refusing to escape `data_dir`."""
    path = data_dir / name
    if path.parent.resolve() != data_dir.resolve():
        raise ValueError(f"unsafe record file name: {name!r}")
    return path


def _short_hash(value: str) -> str:
    """Return a short stable hash, used to disambiguate file names."""
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:8]
