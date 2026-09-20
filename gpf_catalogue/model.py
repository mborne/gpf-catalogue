"""Pivot model exposed by this project.

The model is deliberately flat: a record is a handful of scalar fields, not a tree.
It is the format a search index, and ultimately a LLM, consumes. See `docs/model.md`
for the rationale and `scripts/export_schema.py` to regenerate the JSON schema.

This first version only carries what is needed to identify and describe a resource.
Producer, contacts and service links are planned for the next iteration (see ROADMAP.md).
"""

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


class CatalogueRecord(BaseModel):
    """A resource of the Géoplateforme catalogue, flattened.

    Attributes:
        file_identifier: Stable identifier of the metadata record, as used by the
            CSW service (`GetRecordById&ID=...`) and by cartes.gouv.fr URLs.
        type: Kind of resource described by the record.
        title: Human readable name of the resource, `None` when the source record
            does not provide one. A handful of records of the catalogue have no
            title at all; they are kept rather than dropped, so that the gap stays
            visible instead of being silently fabricated from the identifier.
        abstract: Free text description of the resource, `None` when the source
            record does not provide one.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="forbid",
    )

    # Descriptions are carried by the fields themselves so that the exported JSON
    # schema documents the model for its consumers, humans and models alike.
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
