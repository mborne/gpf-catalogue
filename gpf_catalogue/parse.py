"""Conversion of ISO 19115-3 records into the pivot model.

`parse_record()` is a pure function over bytes: it performs no I/O and no network
access, which makes it the part of the pipeline covered by unit tests.

ISO leaves several ways to express the same string. A title can be a plain
`gco:CharacterString`, a `gcx:Anchor` pointing at a register, or a multilingual
`lan:PT_FreeText`. `_text()` resolves all three in one place, so every field added
later inherits the same behaviour.
"""
# Author: Claude (Anthropic) — this file is AI generated, see docs/init.md.

import logging
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from gpf_catalogue.model import CatalogueRecord, ResourceType
from gpf_catalogue.namespaces import NAMESPACES
from gpf_catalogue.storage import json_path, stem_of

logger = logging.getLogger(__name__)

#: Identification block, depending on the kind of resource described.
_IDENTIFICATION_PATHS = (
    "mdb:identificationInfo/mri:MD_DataIdentification",
    "mdb:identificationInfo/srv:SV_ServiceIdentification",
)


class ParseError(Exception):
    """Raised when a record cannot be converted into the pivot model."""


def parse_record(xml_bytes: bytes) -> CatalogueRecord:
    """Convert an ISO 19115-3 record into a `CatalogueRecord`.

    Args:
        xml_bytes: Either a `csw:GetRecordByIdResponse` body or a bare
            `mdb:MD_Metadata` document.

    Returns:
        The record in the pivot model.

    Raises:
        ParseError: If the document is not a usable metadata record, i.e. if it
            holds no ISO record, no identifier or no identification block.
    """
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as cause:
        raise ParseError(f"invalid XML: {cause}") from cause

    metadata = _find_metadata(root)

    identifier = _text(
        metadata.find("mdb:metadataIdentifier/mcc:MD_Identifier/mcc:code", NAMESPACES)
    )
    if not identifier:
        raise ParseError("missing mdb:metadataIdentifier")

    identification = _find_identification(metadata)
    if identification is None:
        raise ParseError(f"{identifier}: missing mdb:identificationInfo")

    title = _text(
        identification.find("mri:citation/cit:CI_Citation/cit:title", NAMESPACES)
    )
    if not title:
        # Around a dozen records of the catalogue carry no title. Reporting the
        # gap is more useful than dropping the record or inventing a title.
        logger.warning("%s: no title", identifier)

    return CatalogueRecord(
        file_identifier=identifier,
        type=_resource_type(metadata, identification),
        title=title,
        abstract=_text(identification.find("mri:abstract", NAMESPACES)),
    )


def _find_metadata(root: ET.Element) -> ET.Element:
    """Return the `mdb:MD_Metadata` element, unwrapping the CSW envelope if any.

    Raises:
        ParseError: If the document holds no ISO 19115-3 record.
    """
    if root.tag == f"{{{NAMESPACES['mdb']}}}MD_Metadata":
        return root
    metadata = root.find(".//mdb:MD_Metadata", NAMESPACES)
    if metadata is None:
        raise ParseError(
            "no mdb:MD_Metadata found (is the record an ISO 19115-3 document?)"
        )
    return metadata


def _find_identification(metadata: ET.Element) -> ET.Element | None:
    """Return the identification block, whichever kind of resource is described."""
    for path in _IDENTIFICATION_PATHS:
        identification = metadata.find(path, NAMESPACES)
        if identification is not None:
            return identification
    return None


def _resource_type(metadata: ET.Element, identification: ET.Element) -> ResourceType:
    """Return the kind of resource described by the record.

    Reads `MD_ScopeCode`, and falls back on the kind of identification block when
    the scope is absent or holds a value outside of `ResourceType`.
    """
    for scope in metadata.iterfind(
        "mdb:metadataScope/mdb:MD_MetadataScope/mdb:resourceScope/mcc:MD_ScopeCode",
        NAMESPACES,
    ):
        code = (scope.get("codeListValue") or "").strip()
        try:
            return ResourceType(code)
        except ValueError:
            logger.warning("unsupported MD_ScopeCode %r, falling back", code)

    is_service = identification.tag == f"{{{NAMESPACES['srv']}}}SV_ServiceIdentification"
    return ResourceType.SERVICE if is_service else ResourceType.DATASET


def _text(parent: ET.Element | None) -> str | None:
    """Return the string carried by an ISO character string property.

    Handles the three encodings found in the Géoplateforme catalogue, in order of
    preference: `gco:CharacterString`, `gcx:Anchor` and, for multilingual values
    with no default locale, the first `lan:LocalisedCharacterString`.

    Args:
        parent: The property element, e.g. `mri:abstract`. May be `None`, which
            makes calling code simpler.

    Returns:
        The stripped text, or `None` when the property is absent or empty.
    """
    if parent is None:
        return None
    for path in (
        "gco:CharacterString",
        "gcx:Anchor",
        "lan:PT_FreeText/lan:textGroup/lan:LocalisedCharacterString",
    ):
        for element in parent.iterfind(path, NAMESPACES):
            text = (element.text or "").strip()
            if text:
                return text
    return None


@dataclass
class ParseReport:
    """Outcome of a conversion run.

    Attributes:
        total: Number of raw records found on disk.
        written: Number of pivot records written.
        by_type: Number of records per resource type.
        missing_title: Number of records written without a title.
        missing_abstract: Number of records written without an abstract.
        failed: `(file name, reason)` for each record that could not be converted.
    """

    total: int = 0
    written: int = 0
    by_type: Counter[str] = field(default_factory=Counter)
    missing_title: int = 0
    missing_abstract: int = 0
    failed: list[tuple[str, str]] = field(default_factory=list)


def parse_file(path: Path) -> CatalogueRecord:
    """Convert one harvested record file into the pivot model.

    Raises:
        ParseError: If the file is not a usable metadata record.
    """
    return parse_record(path.read_bytes())


def parse_all(data_dir: Path) -> ParseReport:
    """Convert every `*.xml` of `data_dir` into its `*.json` counterpart.

    Conversion is cheap and the whole point is to reflect the current parser, so
    existing JSON files are always rewritten.

    Args:
        data_dir: Directory holding the harvested records.

    Returns:
        A report of what was converted and what failed.
    """
    report = ParseReport()
    for path in sorted(data_dir.glob("*.xml")):
        report.total += 1
        try:
            record = parse_file(path)
        except ParseError as cause:
            logger.error("failed to parse %s: %s", path.name, cause)
            report.failed.append((path.name, str(cause)))
            continue

        # The JSON sits next to the XML it was built from, so the naming rules of
        # the harvest apply without having to recompute them here.
        target = json_path(data_dir, stem_of(path))
        target.write_text(
            record.model_dump_json(by_alias=True, indent=2) + "\n", encoding="utf-8"
        )
        report.written += 1
        report.by_type[record.type.value] += 1
        report.missing_title += record.title is None
        report.missing_abstract += record.abstract is None
        logger.debug("wrote %s", target.name)

    return report
