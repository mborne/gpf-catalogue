"""Pivot model exposed by this project.

The model is deliberately flat: a record is a handful of scalar fields and lists of
scalars, not a tree. It is the format a search index, and ultimately a LLM, consumes.
See `docs/model.md` for the rationale and `scripts/export_schema.py` to regenerate the
JSON schema.

`Link` and `Extent` are the two exceptions to the "no sub-object" rule, for the same
reason: an access endpoint is only usable as a `(type, url)` pair, and a named coverage
zone is only usable as a `(name, bbox)` pair. Splitting either into parallel lists would
lose which name belongs to which URL, or which box is "Guadeloupe". See
`docs/model.md#why-links-are-objects`.
"""
# Author: Claude (Anthropic) — this file is AI generated, see docs/init.md.

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class ResourceType(StrEnum):
    """Kind of resource described by a metadata record.

    Values mirror the ISO `MD_ScopeCode` code list, restricted to the values
    actually used by the Géoplateforme catalogue.
    """

    DATASET = "dataset"
    """A single dataset, e.g. a specific delivery of a product."""

    SERIES = "series"
    """A collection of homogeneous datasets, e.g. BD TOPO® as a whole."""

    SERVICE = "service"
    """A web service, e.g. the altimetry computation API."""


class SpatialScope(StrEnum):
    """Extent a resource is meant to describe, from the INSPIRE code list.

    Values are the last segment of the code list URI
    `http://inspire.ec.europa.eu/metadata-codelist/SpatialScope`, which the
    catalogue publishes as the `xlink:href` of a keyword anchor. They answer
    "is this a national product or a local one?", which is the cheapest filter
    a search can apply before looking at a bounding box.
    """

    GLOBAL = "global"
    """Worldwide coverage."""

    EUROPEAN = "european"
    """Coverage of Europe, or of the European Union."""

    NATIONAL = "national"
    """Coverage of the country, here France and its overseas territories."""

    REGIONAL = "regional"
    """Coverage of a region, a department or a comparable subdivision."""

    LOCAL = "local"
    """Coverage of a municipality or a smaller area."""


class LinkType(StrEnum):
    """What a link leads to.

    The catalogue leaves `cit:protocol` empty on 85 % of its links, so the type is
    inferred from the URL when the protocol is missing (see `gpf_catalogue.parse`).
    The point of typing is that a consumer can act on a link without opening it.
    """

    WFS = "wfs"
    """OGC Web Feature Service endpoint, to query vector features."""

    WMS = "wms"
    """OGC Web Map Service endpoint, to render a map image."""

    WMTS = "wmts"
    """OGC Web Map Tile Service endpoint."""

    TMS = "tms"
    """Tile Map Service endpoint, vector or raster tiles."""

    DOWNLOAD = "download"
    """Direct download of the data itself."""

    CAPABILITIES = "capabilities"
    """A service capabilities document, not the service endpoint itself."""

    DOCUMENTATION = "documentation"
    """Human readable documentation, typically a PDF or a web page."""

    OTHER = "other"
    """A link the pipeline could not type. Kept rather than dropped."""


class BaseRecordModel(BaseModel):
    """Shared configuration: camelCase in JSON, snake_case in Python."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="forbid",
    )


class Link(BaseRecordModel):
    """An access endpoint of a resource.

    Attributes:
        type: What the link leads to.
        url: The absolute URL, as published by the catalogue.
        name: Label given by the catalogue — often a layer, `BDTOPO_V3:batiment`.
        description: Human readable label of the same entry, "BD TOPO® V3 batiment".
    """

    type: LinkType = Field(description="What the link leads to.")
    url: str = Field(description="Absolute URL of the endpoint.")
    name: str | None = Field(
        default=None,
        description=(
            "Label published for this entry, null when the catalogue gives none. On "
            "a service it is usually the layer or feature type reached at that URL, "
            "e.g. `BDTOPO_V3:batiment`."
        ),
    )
    description: str | None = Field(
        default=None,
        description=(
            "Human readable label of the same entry, e.g. 'BD TOPO® V3 batiment'. "
            "Null when the catalogue gives none; it differs from `name` on 2 212 of "
            "the 2 243 entries carrying both."
        ),
    )


class Extent(BaseRecordModel):
    """One geographic extent of a resource, with the name the catalogue gave it.

    A record often declares one extent per territory it covers: `IGNF_BD-TOPO`
    publishes eight, from "France métropolitaine" to "Saint-Martin", each with its
    own box and its ISO 3166 alpha-3 code. `CatalogueRecord.bbox` is their union,
    which for that record spans the Atlantic and the Indian Ocean; this is the
    detail that says what is actually covered.

    Attributes:
        name: Label published for the zone, e.g. "Guadeloupe".
        code: Code identifying the zone, e.g. "GLP".
        code_space: Title of the authority the code belongs to.
        bbox: The zone's own box, `[west, south, east, north]` in decimal degrees.
    """

    name: str | None = Field(
        default=None,
        description=(
            "Label published for this zone, e.g. 'Guadeloupe'. Null when the "
            "catalogue names the extent without describing it, which is the case "
            "of 167 of the 580 extents of the catalogue."
        ),
    )
    code: str | None = Field(
        default=None,
        description=(
            "Code identifying the zone, e.g. 'GLP'. Null when the extent carries "
            "no geographic identifier."
        ),
    )
    code_space: str | None = Field(
        default=None,
        description=(
            "Title of the authority `code` belongs to, e.g. 'ISO 3166 alpha 3'. "
            "Null when the identifier cites none."
        ),
    )
    bbox: list[float] = Field(
        description=(
            "Box of this zone alone, as [west, south, east, north] in decimal "
            "degrees (WGS 84), in GeoJSON order. An extent whose box is absent or "
            "half declared is not published at all, rather than completed."
        )
    )


class CatalogueRecord(BaseRecordModel):
    """A resource of the Géoplateforme catalogue, flattened.

    Every field but `file_identifier` and `type` is optional, because the catalogue
    publishes records that lack almost anything. A field the catalogue does not
    provide is `None` or an empty list, never invented.
    """

    # Descriptions are carried by the fields themselves so that the exported JSON
    # schema documents the model for its consumers, humans and models alike.

    # --- identity ------------------------------------------------------------
    file_identifier: str = Field(
        description=(
            "Stable identifier of the metadata record, usable to fetch it again "
            "from the CSW service or to build its cartes.gouv.fr URL."
        )
    )
    type: ResourceType = Field(description="Kind of resource described by the record.")
    title: str | None = Field(
        default=None,
        description="Human readable name of the resource, null when it has none.",
    )
    abstract: str | None = Field(
        default=None,
        description="Free text description of the resource, null when it has none.",
    )
    edition: str | None = Field(
        default=None,
        description=(
            "Version of the resource as its citation states it, e.g. '3.5' for "
            "BD TOPO®. Read from the resource citation only: `cit:edition` also "
            "appears in every distribution format citation, where it says "
            "'inapplicable'. Null when the citation states none."
        ),
    )

    # --- provenance ----------------------------------------------------------
    producer: str | None = Field(
        default=None,
        description=(
            "Organisation responsible for the resource, read from its point of "
            "contact. Null when the record names none."
        ),
    )
    contact_email: str | None = Field(
        default=None,
        description="Contact email address of the producer, null when absent.",
    )

    # --- what it is about ----------------------------------------------------
    keywords: list[str] = Field(
        default_factory=list,
        description=(
            "Free and controlled keywords, deduplicated, in the order the record "
            "publishes them. Empty when the record carries none."
        ),
    )
    inspire_themes: list[str] = Field(
        default_factory=list,
        description=(
            "Keywords coming from the GEMET INSPIRE themes thesaurus, a controlled "
            "vocabulary usable as a search facet. A subset of `keywords`."
        ),
    )
    topic_categories: list[str] = Field(
        default_factory=list,
        description=(
            "ISO 19115 topic categories (`MD_TopicCategoryCode`), e.g. `environment`."
        ),
    )
    purpose: str | None = Field(
        default=None,
        description=(
            "What the resource is meant to be used for, as free text. Answers a "
            "different question from `abstract`, which says what it contains. "
            "Null when the record states none."
        ),
    )

    # --- where and when ------------------------------------------------------
    spatial_scope: SpatialScope | None = Field(
        default=None,
        description=(
            "Extent the resource is meant to describe, from the INSPIRE "
            "`SpatialScope` code list, read from the code the record cites and not "
            "from its label. Null when the record cites none, which is the "
            "majority of the catalogue."
        ),
    )
    bbox: list[float] | None = Field(
        default=None,
        description=(
            "Geographic extent as [west, south, east, north] in decimal degrees "
            "(WGS 84), in GeoJSON order. The union of every box in `extents`, which "
            "makes it a cheap first filter but a coarse one: a record covering "
            "mainland France and the overseas territories gets a box reaching from "
            "the Caribbean to Réunion, up to 3 519 times the area actually covered. "
            "Read `extents` before concluding that a resource covers a point. Null "
            "when the record declares no usable box."
        ),
    )
    extents: list[Extent] = Field(
        default_factory=list,
        description=(
            "The boxes the record declares, one entry each, with the name and code "
            "published for them. An extent carrying no usable box — a purely "
            "temporal one, for instance — is not listed here. Empty when the record "
            "declares none."
        ),
    )
    temporal_start: str | None = Field(
        default=None,
        description="Start of the temporal extent, ISO 8601, null when absent.",
    )
    temporal_end: str | None = Field(
        default=None,
        description="End of the temporal extent, ISO 8601, null when absent.",
    )
    created: str | None = Field(
        default=None,
        description="Creation date of the resource, ISO 8601, null when absent.",
    )
    published: str | None = Field(
        default=None,
        description="Publication date of the resource, ISO 8601, null when absent.",
    )
    revised: str | None = Field(
        default=None,
        description="Last revision date of the resource, ISO 8601, null when absent.",
    )
    update_frequency: str | None = Field(
        default=None,
        description=(
            "How often the resource is updated, as the `MD_MaintenanceFrequencyCode` "
            "value the record publishes, e.g. 'quarterly' or 'notPlanned'. Kept "
            "verbatim and not validated against the ISO code list, because the "
            "catalogue publishes 'quaterly' (sic) on one record and a misspelling is "
            "not something to repair silently. Null when the record states none."
        ),
    )

    # --- how it was made -----------------------------------------------------
    lineage: str | None = Field(
        default=None,
        description=(
            "How the resource was produced, as free text: sources, methods and the "
            "accuracy they imply. Null when the record states none, which includes "
            "the 103 records publishing an empty statement."
        ),
    )

    # --- what may be done with it -------------------------------------------
    licence: str | None = Field(
        default=None,
        description=(
            "Licence or use condition, as free text published by the catalogue "
            "(e.g. 'Licence Ouverte / Open License'). Null when the record states none."
        ),
    )
    access_constraint: str | None = Field(
        default=None,
        description=(
            "Limitation on public access, as free text (e.g. 'Pas de restriction "
            "d'accès public selon INSPIRE'). Null when the record states none."
        ),
    )

    # --- how to reach the data ----------------------------------------------
    links: list[Link] = Field(
        default_factory=list,
        description=(
            "Access endpoints, one per (type, url); the catalogue publishes one "
            "entry per layer, collected into `layers`. Empty when the record "
            "publishes none."
        ),
    )
    thumbnail_url: str | None = Field(
        default=None,
        description=(
            "URL of a preview image of the resource, published as a browse graphic. "
            "Null when the record carries none."
        ),
    )

    # --- catalogue hygiene ---------------------------------------------------
    suspected_test: bool = Field(
        default=False,
        description=(
            "True when the record looks like a test record published by mistake "
            "(e.g. titled 'test'). A heuristic, exposed so that a consumer can "
            "filter it out rather than having to rediscover it."
        ),
    )
