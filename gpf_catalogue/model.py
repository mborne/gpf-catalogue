"""Pivot model exposed by this project.

The model is deliberately flat: a record is a handful of scalar fields and lists of
scalars, not a tree. It is the format a search index, and ultimately a LLM, consumes.
See `docs/model.md` for the rationale and `scripts/export_schema.py` to regenerate the
JSON schema.

`Link` is the single exception to the "no sub-object" rule: an access endpoint is only
usable as a `(type, url)` pair, and splitting it into parallel lists would lose which
name belongs to which URL. See `docs/model.md#why-links-are-objects`.
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
        name: Label given by the catalogue, `None` on the 291 links that carry none.
    """

    type: LinkType = Field(description="What the link leads to.")
    url: str = Field(description="Absolute URL of the endpoint.")
    name: str | None = Field(
        default=None,
        description="Label given by the catalogue, null when it publishes none.",
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

    # --- where and when ------------------------------------------------------
    bbox: list[float] | None = Field(
        default=None,
        description=(
            "Geographic extent as [west, south, east, north] in decimal degrees "
            "(WGS 84), in GeoJSON order. The union of every bounding box the record "
            "declares. Null when the record declares none."
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
            "Access endpoints, deduplicated on (type, url). Empty when the record "
            "publishes none."
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
