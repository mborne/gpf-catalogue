"""Conversion of ISO 19115-3 records into the pivot model.

`parse_record()` is a pure function over bytes: it performs no I/O and no network
access, which makes it the part of the pipeline covered by unit tests.

ISO leaves several ways to express the same string. A title can be a plain
`gco:CharacterString`, a `gcx:Anchor` pointing at a register, or a multilingual
`lan:PT_FreeText`. `_text()` resolves all three in one place, so every field added
later inherits the same behaviour.

Every extraction rule below was derived from the 333 records of the live catalogue,
not from the standard: ISO allows far more than the Géoplateforme actually publishes,
and guessing at the rest would add code no record exercises.
"""
# Author: Claude (Anthropic) — this file is AI generated, see docs/init.md.

import json
import logging
import re
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

from gpf_catalogue.model import (
    CatalogueRecord,
    Extent,
    Link,
    LinkType,
    ResourceType,
    SpatialScope,
)
from gpf_catalogue.namespaces import NAMESPACES
from gpf_catalogue.storage import json_path, stem_of

logger = logging.getLogger(__name__)

#: Identification block, depending on the kind of resource described.
_IDENTIFICATION_PATHS = (
    "mdb:identificationInfo/mri:MD_DataIdentification",
    "mdb:identificationInfo/srv:SV_ServiceIdentification",
)

#: Thesaurus titles whose keywords are INSPIRE themes. The catalogue spells the
#: same thesaurus in several ways, hence a normalized comparison.
_INSPIRE_THESAURI = ("gemet - inspire themes", "gemet inspire themes")

#: Code list the INSPIRE spatial scope keywords are taken from. The catalogue cites
#: it as the `xlink:href` of the keyword anchor itself, so the code is read from the
#: keyword and the thesaurus block never has to be matched — which is just as well,
#: since its title is spelled both "INSPIRE Spatial Scope" and "INSPIRE Spatial scope".
_SPATIAL_SCOPE_CODELIST = "http://inspire.ec.europa.eu/metadata-codelist/SpatialScope/"

#: `cit:protocol` values met in the catalogue, normalized to a link type. Only 15 %
#: of the links carry a protocol at all; the rest are typed from their URL.
_PROTOCOLS = {
    "ogc:wms": LinkType.WMS,
    "ogc web map service": LinkType.WMS,
    "ogc:wfs": LinkType.WFS,
    "ogc web feature service": LinkType.WFS,
    "ogc:wmts": LinkType.WMTS,
    "ogc:tms": LinkType.TMS,
    "tms": LinkType.TMS,
    "www:download-1.0-http--download": LinkType.DOWNLOAD,
    "www:link-1.0-http--link": LinkType.DOCUMENTATION,
}

#: First path segment of a `data.geopf.fr` URL, normalized to a link type. The
#: Géoplateforme serves each protocol under its own prefix, `wms-v` and `wms-r`
#: being the vector and raster flavours of the same service.
_URL_SEGMENTS = {
    "wfs": LinkType.WFS,
    "wms": LinkType.WMS,
    "wms-v": LinkType.WMS,
    "wms-r": LinkType.WMS,
    "wmts": LinkType.WMTS,
    "tms": LinkType.TMS,
    "telechargement": LinkType.DOWNLOAD,
}

#: File extensions that make a link a document rather than an endpoint.
_DOCUMENT_SUFFIXES = (".pdf", ".html", ".htm", ".txt", ".md", ".odt", ".docx")

#: File extensions that make a link a direct download of data. Styling files
#: (`.qml`, `.sld`, `.qgz`) are deliberately absent: they describe how to draw a
#: layer, not the layer itself, and stay typed `other`.
_DOWNLOAD_SUFFIXES = (".zip", ".7z", ".gz", ".tar", ".csv", ".gpkg", ".shp")

#: Tokens that make a record look like a test publication. Deliberately short:
#: the field is called `suspectedTest`, and a loose rule would flag real records
#: such as `test_openig`, titled "Communes de l'Hérault (34)".
_TEST_TOKENS = frozenset(
    {"test", "tests", "essai", "essais", "demo", "toto", "lls", "aaa", "xxx"}
)

#: `cit:CI_Date` types, mapped to the pivot field they feed.
_DATE_TYPES = {
    "creation": "created",
    "publication": "published",
    "revision": "revised",
    "lastupdate": "revised",
}


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

    # Anchored on the resource citation on purpose: `cit:edition` also hangs under
    # every distribution format citation, where `IGNF_BD-TOPO` says "inapplicable"
    # 9 times against the one edition of the product itself, "3.5".
    edition = _text(
        identification.find("mri:citation/cit:CI_Citation/cit:edition", NAMESPACES)
    )
    abstract = _text(identification.find("mri:abstract", NAMESPACES))
    keywords, inspire_themes = _keywords(identification)
    dates = _dates(identification)
    licence, access_constraint = _constraints(identification)
    start, end = _temporal_extent(identification)
    # Read once: `bbox` is the union of these, not a second walk of the document.
    extents = _extents(identification)

    return CatalogueRecord(
        file_identifier=identifier,
        type=_resource_type(metadata, identification),
        title=title,
        abstract=abstract,
        edition=edition,
        producer=_producer(metadata, identification),
        contact_email=_contact_email(metadata, identification),
        keywords=keywords,
        inspire_themes=inspire_themes,
        topic_categories=_topic_categories(identification),
        purpose=_text(identification.find("mri:purpose", NAMESPACES)),
        spatial_scope=_spatial_scope(identification),
        bbox=_union_bbox(extents),
        extents=extents,
        temporal_start=start,
        temporal_end=end,
        created=dates.get("created"),
        published=dates.get("published"),
        revised=dates.get("revised"),
        update_frequency=_update_frequency(identification),
        lineage=_lineage(metadata),
        licence=licence,
        access_constraint=access_constraint,
        links=_links(metadata),
        thumbnail_url=_thumbnail_url(identification),
        suspected_test=_suspected_test(identifier, title, abstract),
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

    is_service = (
        identification.tag == f"{{{NAMESPACES['srv']}}}SV_ServiceIdentification"
    )
    return ResourceType.SERVICE if is_service else ResourceType.DATASET


def _responsibilities(
    metadata: ET.Element, identification: ET.Element
) -> list[ET.Element]:
    """Return the responsible parties of a record, most specific first.

    The resource point of contact describes the producer; the metadata contact
    describes whoever published the record, and is only a fallback.
    """
    return [
        *identification.findall("mri:pointOfContact/cit:CI_Responsibility", NAMESPACES),
        *identification.findall(
            "mri:citation/cit:CI_Citation/cit:citedResponsibleParty"
            "/cit:CI_Responsibility",
            NAMESPACES,
        ),
        *metadata.findall("mdb:contact/cit:CI_Responsibility", NAMESPACES),
    ]


def _producer(metadata: ET.Element, identification: ET.Element) -> str | None:
    """Return the organisation responsible for the resource."""
    for responsibility in _responsibilities(metadata, identification):
        name = _text(
            responsibility.find("cit:party/cit:CI_Organisation/cit:name", NAMESPACES)
        )
        if name:
            return name
    return None


def _contact_email(metadata: ET.Element, identification: ET.Element) -> str | None:
    """Return the contact email address of the producer."""
    for responsibility in _responsibilities(metadata, identification):
        email = _text(
            responsibility.find(
                ".//cit:CI_Address/cit:electronicMailAddress", NAMESPACES
            )
        )
        if email:
            return email
    return None


def _keywords(identification: ET.Element) -> tuple[list[str], list[str]]:
    """Return every keyword, and the subset coming from the INSPIRE thesaurus.

    Returns:
        `(keywords, inspire_themes)`, both deduplicated and in publication order.
    """
    keywords: dict[str, None] = {}
    inspire: dict[str, None] = {}
    for block in identification.iterfind(
        "mri:descriptiveKeywords/mri:MD_Keywords", NAMESPACES
    ):
        thesaurus = _text(
            block.find("mri:thesaurusName/cit:CI_Citation/cit:title", NAMESPACES)
        )
        normalized = (thesaurus or "").strip().casefold()
        is_inspire = any(normalized.startswith(name) for name in _INSPIRE_THESAURI)
        for element in block.iterfind("mri:keyword", NAMESPACES):
            value = _text(element)
            if not value:
                continue
            keywords[value] = None
            if is_inspire:
                inspire[value] = None
    return list(keywords), list(inspire)


def _topic_categories(identification: ET.Element) -> list[str]:
    """Return the ISO topic categories declared by the record."""
    categories: dict[str, None] = {}
    for element in identification.iterfind(
        "mri:topicCategory/mri:MD_TopicCategoryCode", NAMESPACES
    ):
        value = (element.text or "").strip()
        if value:
            categories[value] = None
    return list(categories)


def _spatial_scope(identification: ET.Element) -> SpatialScope | None:
    """Return the INSPIRE spatial scope cited by the record, if any.

    136 of the 326 records carry it, always as a single `gcx:Anchor` keyword whose
    `xlink:href` points into the INSPIRE `SpatialScope` code list. The **code** is
    read, never the label: the two disagree on 6 records, which cite
    `…/SpatialScope/global` under the label "National", and the labels alone spell
    two codes four ways ("National", "Nationales", "Régional", "regional").

    Returns:
        The scope, or `None` when the record cites none — the majority of the
        catalogue — or cites a code outside the pivot enumeration.
    """
    for anchor in identification.iterfind(
        "mri:descriptiveKeywords/mri:MD_Keywords/mri:keyword/gcx:Anchor", NAMESPACES
    ):
        href = (anchor.get(f"{{{NAMESPACES['xlink']}}}href") or "").strip()
        if not href.startswith(_SPATIAL_SCOPE_CODELIST):
            continue
        code = href[len(_SPATIAL_SCOPE_CODELIST) :].strip("/").casefold()
        try:
            return SpatialScope(code)
        except ValueError:
            # A code INSPIRE added, or a typo in the URI: reported, not guessed at
            # from the label, which is what disagrees with the code in the first place.
            logger.warning("unsupported SpatialScope %r", href)
    return None


def _extents(identification: ET.Element) -> list[Extent]:
    """Return every geographic extent of the record, with the name it carries.

    A record covering several territories publishes one `gex:EX_Extent` per
    territory: `IGNF_BD-TOPO` declares eight, from "France métropolitaine" to
    "Saint-Martin", each with its own box and its ISO 3166 alpha-3 code. Keeping
    them apart is the point — their union spans the Atlantic and the Indian Ocean
    and covers 65 times the area the product actually describes.

    An extent carrying no usable box produces no entry: that is how the 115
    purely temporal extents of the catalogue ("Dates de publication") stay out,
    without their label being mistaken for a place.

    Returns:
        One `Extent` per box, in the order the record publishes them. Empty when
        the record declares no usable box.
    """
    extents: list[Extent] = []
    for block in identification.iterfind("mri:extent/gex:EX_Extent", NAMESPACES):
        name = _text(block.find("gex:description", NAMESPACES))
        code, code_space = _geographic_identifier(block)
        for box in block.iterfind(
            "gex:geographicElement/gex:EX_GeographicBoundingBox", NAMESPACES
        ):
            values = [
                _decimal(box.find(f"gex:{side}", NAMESPACES))
                for side in (
                    "westBoundLongitude",
                    "southBoundLatitude",
                    "eastBoundLongitude",
                    "northBoundLatitude",
                )
            ]
            if any(value is None for value in values):
                # A partial box cannot be used without inventing its missing side.
                logger.debug("skipping incomplete bounding box %r", values)
                continue
            extents.append(
                Extent(name=name, code=code, code_space=code_space, bbox=values)
            )
    return extents


def _geographic_identifier(block: ET.Element) -> tuple[str | None, str | None]:
    """Return the `(code, code_space)` a `gex:EX_Extent` names its zone by.

    The code is read from `mcc:code` and its authority from the title of the
    citation carrying it — "FXX" under "ISO 3166 alpha 3". Both are `None` when
    the extent publishes no geographic description, which is the case of 167 of
    the 580 extents of the catalogue.
    """
    identifier = block.find(
        "gex:geographicElement/gex:EX_GeographicDescription/"
        "gex:geographicIdentifier/mcc:MD_Identifier",
        NAMESPACES,
    )
    if identifier is None:
        return None, None
    code = _text(identifier.find("mcc:code", NAMESPACES))
    code_space = _text(
        identifier.find("mcc:authority/cit:CI_Citation/cit:title", NAMESPACES)
    )
    return code, code_space


def _union_bbox(extents: list[Extent]) -> list[float] | None:
    """Return the union of the boxes of `extents`.

    The union answers "could this resource cover my area?" in one comparison,
    which is why it is kept as `CatalogueRecord.bbox`. It is deliberately a coarse
    answer: `ENR_CONSO-ELECTRICITE-COMMUNE` declares four territories whose union
    is 3 519 times their combined area. `extents` is the precise one.

    Returns:
        `[west, south, east, north]` in decimal degrees (GeoJSON order), or `None`
        when `extents` is empty.
    """
    if not extents:
        return None
    boxes = [extent.bbox for extent in extents]
    return [
        min(box[0] for box in boxes),
        min(box[1] for box in boxes),
        max(box[2] for box in boxes),
        max(box[3] for box in boxes),
    ]


def _update_frequency(identification: ET.Element) -> str | None:
    """Return the maintenance frequency the record publishes, verbatim.

    Read from `@codeListValue`, the code and not its label, like every other code
    list value of this model. It stays a plain string rather than an enumeration
    because the catalogue publishes `quaterly` (sic) on one record next to
    `quarterly` on five others: rejecting or silently repairing the typo would
    either drop a real record or state something the catalogue did not.

    Returns:
        The code, e.g. `quarterly` or `notPlanned`, or `None` when absent.
    """
    code = identification.find(
        "mri:resourceMaintenance/mmi:MD_MaintenanceInformation/"
        "mmi:maintenanceAndUpdateFrequency/mmi:MD_MaintenanceFrequencyCode",
        NAMESPACES,
    )
    if code is None:
        return None
    return (code.get("codeListValue") or "").strip() or None


def _lineage(metadata: ET.Element) -> str | None:
    """Return the statement saying how the resource was produced.

    Unlike almost everything else in the model this hangs under `mdb:MD_Metadata`
    and not under the identification block. 103 records publish the element with
    no text at all, which `_text` already turns into `None`.
    """
    return _text(
        metadata.find("mdb:resourceLineage/mrl:LI_Lineage/mrl:statement", NAMESPACES)
    )


def _thumbnail_url(identification: ET.Element) -> str | None:
    """Return the URL of the record's browse graphic, or `None`.

    The file name of a `mcc:MD_BrowseGraphic` is an absolute URL throughout this
    catalogue. The first one wins, as everywhere else in this parser.
    """
    return _text(
        identification.find(
            "mri:graphicOverview/mcc:MD_BrowseGraphic/mcc:fileName", NAMESPACES
        )
    )


def _temporal_extent(identification: ET.Element) -> tuple[str | None, str | None]:
    """Return the start and end of the temporal extent.

    A record may declare several periods; the widest span is kept, so that a
    consumer asking "is this resource relevant for 2020?" gets one answer.
    """
    starts, ends = [], []
    for period in identification.iterfind(
        ".//gex:temporalElement//gml:TimePeriod", NAMESPACES
    ):
        start = (period.findtext("gml:beginPosition", namespaces=NAMESPACES) or "").strip()
        end = (period.findtext("gml:endPosition", namespaces=NAMESPACES) or "").strip()
        if start:
            starts.append(start)
        if end:
            ends.append(end)
    return (min(starts) if starts else None, max(ends) if ends else None)


def _dates(identification: ET.Element) -> dict[str, str]:
    """Return the citation dates of the resource, keyed by pivot field name.

    The first date of a given type wins: a handful of records publish the same
    type twice, and preferring the first keeps the result stable.
    """
    dates: dict[str, str] = {}
    for date in identification.iterfind(
        "mri:citation/cit:CI_Citation/cit:date/cit:CI_Date", NAMESPACES
    ):
        code = date.find("cit:dateType/cit:CI_DateTypeCode", NAMESPACES)
        kind = _DATE_TYPES.get((code.get("codeListValue") or "").strip().casefold())
        if kind is None or kind in dates:
            continue
        value = _date_text(date.find("cit:date", NAMESPACES))
        if value:
            dates[kind] = value
    return dates


def _constraints(identification: ET.Element) -> tuple[str | None, str | None]:
    """Return the licence and the access limitation of the resource.

    ISO carries both as free text in `mco:otherConstraints`; what distinguishes
    them is the sibling element of the same `MD_LegalConstraints` block. A block
    declaring `mco:useConstraints` states what may be done with the data, one
    declaring `mco:accessConstraints` states who may reach it. Measured over the
    catalogue, the split is clean: licences on one side, "pas de restriction
    d'accès public" on the other.

    Returns:
        `(licence, access_constraint)`, either of which may be `None`.
    """
    licence = access = None
    for block in identification.iterfind(
        "mri:resourceConstraints/mco:MD_LegalConstraints", NAMESPACES
    ):
        texts = [
            value
            for value in (
                _text(element)
                for element in block.iterfind("mco:otherConstraints", NAMESPACES)
            )
            if value
        ]
        if not texts:
            continue
        if licence is None and block.find("mco:useConstraints", NAMESPACES) is not None:
            licence = texts[0]
        elif (
            access is None
            and block.find("mco:accessConstraints", NAMESPACES) is not None
        ):
            access = texts[0]
    return licence, access


def _links(metadata: ET.Element) -> list[Link]:
    """Return the access endpoints of a record, typed and kept flat.

    The catalogue publishes one `CI_OnlineResource` **per layer**, all carrying the
    same endpoint URL and differing by `cit:name` and `cit:description`:
    `IGNF_BD-TOPO` publishes 109 WFS entries for one WFS URL, named
    `BDTOPO_V3:aerodrome`, `BDTOPO_V3:batiment`, and so on.

    Every entry is kept, one link each. Collapsing them on `(type, url)` — as
    earlier versions did — dropped the layer the entry names, and labelled a whole
    WFS service after whichever layer came first, which reads as *this endpoint
    serves aerodromes*. Grouping and filtering are a presentation concern; the
    pivot model stays flat and keeps what the catalogue published.

    Only **exact** repeats are dropped, the same `(type, url, name, description)`
    published twice, which is 9 entries across the catalogue.
    """
    links: dict[tuple[str, str, str | None, str | None], Link] = {}
    for resource in metadata.iterfind(
        "mdb:distributionInfo/mrd:MD_Distribution//mrd:onLine/cit:CI_OnlineResource",
        NAMESPACES,
    ):
        url = _text(resource.find("cit:linkage", NAMESPACES))
        if not url:
            continue
        protocol = _text(resource.find("cit:protocol", NAMESPACES))
        link = Link(
            type=_link_type(url, protocol),
            url=url,
            name=_text(resource.find("cit:name", NAMESPACES)),
            description=_text(resource.find("cit:description", NAMESPACES)),
        )
        links.setdefault((link.type.value, link.url, link.name, link.description), link)
    return list(links.values())


def _link_type(url: str, protocol: str | None) -> LinkType:
    """Return what a link leads to, from its protocol when given, else its URL.

    The catalogue leaves `cit:protocol` empty on 85 % of its links, so the URL is
    the primary signal in practice.

    A *static* capabilities file is recognized first: it lives under `/annexes/`,
    behind a path no service segment would match. A `?REQUEST=GetCapabilities`
    query is deliberately *not* treated the same way — `.../wfs/ows?…` is the WFS
    endpoint itself, advertised through its capabilities URL, and typing it as a
    document would hide the endpoint from a consumer asking for the WFS.
    """
    path = urlsplit(url).path
    lowered = path.casefold()

    if lowered.endswith("capabilities.xml"):
        return LinkType.CAPABILITIES

    if protocol:
        known = _PROTOCOLS.get(protocol.strip().casefold())
        if known is not None:
            return known

    for segment in (part for part in lowered.split("/") if part):
        known = _URL_SEGMENTS.get(segment)
        if known is not None:
            return known

    if lowered.endswith(_DOCUMENT_SUFFIXES):
        return LinkType.DOCUMENTATION
    if lowered.endswith(_DOWNLOAD_SUFFIXES):
        return LinkType.DOWNLOAD
    return LinkType.OTHER


def _normalize(value: str | None) -> str:
    """Lowercase and reduce a string to space separated alphanumeric words."""
    return " ".join(re.sub(r"[^0-9a-z]+", " ", (value or "").casefold()).split())


def _suspected_test(
    identifier: str, title: str | None, abstract: str | None
) -> bool:
    """Return whether a record looks like a test publication.

    The catalogue publishes test records next to real ones. The rule is kept
    narrow on purpose, and reports a suspicion rather than a verdict: a record is
    flagged when one of its identifier, title or abstract is *entirely* a test
    token, or when its title *begins* with one. Matching a test token anywhere
    would flag `test_openig`, which is titled "Communes de l'Hérault (34)" and is
    a real dataset.
    """
    for value in (identifier, title, abstract):
        words = _normalize(value).split()
        if words and set(words) <= _TEST_TOKENS:
            return True
    title_words = _normalize(title).split()
    return bool(title_words) and title_words[0] in _TEST_TOKENS


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
                return _strip_repeated_href(element, text)
    return None


def _strip_repeated_href(element: ET.Element, text: str) -> str:
    """Drop a trailing URL that merely repeats the element's own `xlink:href`.

    Several records glue the target of an anchor onto its label, so that the
    licence of `IGNF_BD-TOPO` reads "Licence Ouverte / Open License (compatible
    ODC-BY, CC-BY 2.0)https://www.etalab.gouv.fr/...open-licence.pdf". The URL is
    already in `xlink:href`, so removing the exact duplicate loses nothing and
    makes the value readable. Anything that is not a byte for byte repeat of the
    href is left alone.
    """
    href = (element.get(f"{{{NAMESPACES['xlink']}}}href") or "").strip()
    if href and text != href and text.endswith(href):
        return text[: -len(href)].strip() or text
    return text


def _decimal(parent: ET.Element | None) -> float | None:
    """Return the number carried by a `gco:Decimal` property, or `None`."""
    if parent is None:
        return None
    raw = (parent.findtext("gco:Decimal", namespaces=NAMESPACES) or "").strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        logger.warning("unreadable decimal %r", raw)
        return None


def _date_text(parent: ET.Element | None) -> str | None:
    """Return the date carried by a `gco:Date` or `gco:DateTime` property."""
    if parent is None:
        return None
    for path in ("gco:Date", "gco:DateTime"):
        value = (parent.findtext(path, namespaces=NAMESPACES) or "").strip()
        if value:
            return value
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
        coverage: Number of records carrying each optional field.
        links_by_type: Number of links written, per link type.
        suspected_tests: Identifiers of the records flagged as test publications.
        failed: `(file name, reason)` for each record that could not be converted.
    """

    total: int = 0
    written: int = 0
    by_type: Counter[str] = field(default_factory=Counter)
    missing_title: int = 0
    missing_abstract: int = 0
    coverage: Counter[str] = field(default_factory=Counter)
    links_by_type: Counter[str] = field(default_factory=Counter)
    suspected_tests: list[str] = field(default_factory=list)
    failed: list[tuple[str, str]] = field(default_factory=list)


#: Optional fields reported by `ParseReport.coverage`, in display order.
_REPORTED_FIELDS = (
    "title",
    "abstract",
    "edition",
    "producer",
    "contact_email",
    "keywords",
    "inspire_themes",
    "topic_categories",
    "purpose",
    "spatial_scope",
    "bbox",
    "extents",
    "temporal_start",
    "created",
    "published",
    "revised",
    "update_frequency",
    "lineage",
    "licence",
    "access_constraint",
    "links",
    "thumbnail_url",
)


def parse_file(path: Path) -> CatalogueRecord:
    """Convert one harvested record file into the pivot model.

    Raises:
        ParseError: If the file is not a usable metadata record.
    """
    return parse_record(path.read_bytes())


def parse_all(data_dir: Path, catalogue_path: Path | None = None) -> ParseReport:
    """Convert every `*.xml` of `data_dir` into its `*.json` counterpart.

    Conversion is cheap and the whole point is to reflect the current parser, so
    existing JSON files are always rewritten.

    Args:
        data_dir: Directory holding the harvested records.
        catalogue_path: Where to write the aggregated catalogue. Defaults to
            `catalogue.json` beside `data_dir`, deliberately outside of it so it
            can never collide with a record named `catalogue`.

    Returns:
        A report of what was converted and what failed.
    """
    report = ParseReport()
    records: list[CatalogueRecord] = []

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
        records.append(record)
        report.written += 1
        report.by_type[record.type.value] += 1
        report.missing_title += record.title is None
        report.missing_abstract += record.abstract is None
        for name in _REPORTED_FIELDS:
            if getattr(record, name):
                report.coverage[name] += 1
        for link in record.links:
            report.links_by_type[link.type.value] += 1
        if record.suspected_test:
            report.suspected_tests.append(record.file_identifier)
        logger.debug("wrote %s", target.name)

    if catalogue_path is None:
        catalogue_path = data_dir.parent / "catalogue.json"
    write_catalogue(records, catalogue_path)
    return report


def write_catalogue(records: list[CatalogueRecord], path: Path) -> None:
    """Write every pivot record as a single JSON document.

    One file per record suits a mirror; one document suits a consumer that wants
    the whole catalogue in memory, which at this size is the common case.

    The output carries no timestamp on purpose: two runs over the same mirror
    produce the same bytes, so catalogue drift can be diffed (see ROADMAP phase 5).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "source": "https://data.geopf.fr/csw",
        "count": len(records),
        "records": [record.model_dump(by_alias=True) for record in records],
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    logger.info("wrote %s (%d records)", path, len(records))
