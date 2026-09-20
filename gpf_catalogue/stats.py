"""Aggregates over the pivot catalogue.

`compute_stats()` is a pure function over a list of records: it performs no I/O and
no network access, like `parse_record()`, which is what makes it testable offline and
reusable by a future MCP `catalogue_overview` tool.

The aggregates answer the second of the two questions this project started from — *what
data is available on the Géoplateforme?* — which no search index answers. They also
measure what the source metadata is worth, field by field, which is the only honest way
to quote a coverage figure in the documentation.

Two values are **derived** here rather than read from a record, and neither is written
back into the pivot model. Both rules are documented in `docs/overview.md`:

- the publisher is the domain of the contact email, because `producer` is spelled 134
  different ways for far fewer organisations,
- the licence family comes from the explicit mapping of `licence_family()`, because the
  same Licence Ouverte is published under several strings.

Ordering is deterministic everywhere: counts descending, then value ascending. Two runs
over the same catalogue produce the same bytes, for the same reason `catalogue.json`
does (see ROADMAP phase 5).
"""
# Author: Claude (Anthropic) — this file is AI generated, see docs/init.md.

import json
import logging
from collections import Counter
from pathlib import Path

from pydantic import Field

from gpf_catalogue.model import BaseRecordModel, CatalogueRecord

logger = logging.getLogger(__name__)

#: Fields of the pivot model that are never reported as coverage: the two required
#: ones, which are always present, and a flag whose meaning is not "is it filled in".
_NOT_COVERAGE = frozenset({"file_identifier", "type", "suspected_test"})

#: A keyword is only worth showing when several records share it. 432 of the 638
#: keywords of the catalogue are used exactly once, and a list of those answers
#: nothing; keywords remain a search field, not a facet.
KEYWORD_MIN_COUNT = 5

#: Label used when a record declares no licence at all. It is a bucket of its own,
#: and by far the largest one, so it must read as undeclared and never as open.
UNDECLARED_LICENCE = "Undeclared"

#: Licence families, as `(substring to look for, family)` tried in order on the
#: casefolded licence string. The catalogue publishes 10 distinct licence values for
#: what is really a handful of regimes: the same Licence Ouverte appears both bare
#: and with the Etalab URL glued to its label, and three different "conditions
#: générales" name three different producers. Grouping is done by an explicit
#: published rule rather than by string similarity, so that a reader can check it.
LICENCE_FAMILIES: tuple[tuple[str, str], ...] = (
    ("odbl", "ODbL"),
    ("open database license", "ODbL"),
    ("licence ouverte", "Licence Ouverte"),
    ("open license", "Licence Ouverte"),
    ("cartes.gouv.fr/cgu", "Terms of use of cartes.gouv.fr"),
    ("conditions générales", "Terms of use of the producer"),
    ("pas de restriction", "No condition stated"),
    ("aucune restriction", "No condition stated"),
    ("no conditions", "No condition stated"),
)

#: Family given to a licence string matching none of the rules above. It is listed
#: in the quality report rather than hidden: a growing "other" means the mapping
#: needs a new rule.
OTHER_LICENCE = "Other, as published"


class Count(BaseRecordModel):
    """How many records, or links, carry one value.

    Attributes:
        value: The value counted, as displayed.
        count: Number of records, or of links, carrying it.
    """

    value: str = Field(description="The value counted, as displayed.")
    count: int = Field(description="Number of items carrying that value.")


class FieldCoverage(BaseRecordModel):
    """How often an optional field of the pivot model is actually filled in.

    Attributes:
        field: Name of the field, in the JSON spelling of the pivot model.
        count: Number of records carrying a non empty value.
        share: Percentage of the catalogue, rounded to one decimal.
    """

    field: str = Field(description="Field name, as spelled in the pivot JSON.")
    count: int = Field(description="Number of records carrying a value.")
    share: float = Field(description="Percentage of the catalogue, one decimal.")


class QualityStats(BaseRecordModel):
    """What the source metadata is missing, counted rather than described.

    These are properties of the Géoplateforme catalogue, not defects of this
    pipeline. They are published so that they can be acted upon.
    """

    records: int = Field(description="Number of records in the pivot catalogue.")
    missing_title: int = Field(description="Records published without a title.")
    missing_abstract: int = Field(description="Records published without an abstract.")
    suspected_tests: list[str] = Field(
        description="Identifiers of the records flagged as test publications."
    )
    links_total: int = Field(description="Number of links, after deduplication.")
    links_distinct_urls: int = Field(description="Number of distinct URLs among them.")
    links_without_name: int = Field(
        description=(
            "Links carrying neither a name nor a description, so nothing but the "
            "URL says what they lead to."
        )
    )
    links_without_description: int = Field(
        description="Links carrying no `cit:description`."
    )
    records_without_links: int = Field(description="Records offering no access link.")
    distinct_producers: int = Field(
        description=(
            "Distinct spellings of `producer`, which is more than the number of "
            "organisations: IGN alone is spelled three ways."
        )
    )
    undeclared_licence: int = Field(description="Records declaring no licence.")
    undeclared_access_constraint: int = Field(
        description="Records declaring no limitation on public access."
    )


class RecordFacets(BaseRecordModel):
    """The derived values of one record, so the page never recomputes them.

    The overview filters on the publisher and the licence family, both of which are
    derived by rules that live in this module. Reimplementing those rules in
    JavaScript would be two implementations of one rule, and eventually two rules.
    """

    file_identifier: str = Field(description="Identifier of the record described.")
    publisher: str | None = Field(
        description="Contact email domain, null when the record carries no email."
    )
    licence_family: str = Field(description="Family returned by `licence_family()`.")
    year: str | None = Field(
        description="Publication year, null when the record carries no usable date."
    )


class CatalogueStats(BaseRecordModel):
    """Everything the overview displays, computed once from the pivot catalogue.

    The document carries no timestamp on purpose, so that two runs over the same
    catalogue are byte identical and a change is a real change.
    """

    source: str = Field(description="CSW service the catalogue was harvested from.")
    count: int = Field(description="Number of records the statistics cover.")

    by_type: list[Count] = Field(description="Records per resource type.")
    by_topic_category: list[Count] = Field(
        description="Records per ISO topic category. A record may carry several."
    )
    by_inspire_theme: list[Count] = Field(
        description="Records per INSPIRE theme. A record may carry several."
    )
    by_spatial_scope: list[Count] = Field(
        description=(
            "Records per INSPIRE spatial scope. Records citing none are left out "
            "rather than bucketed: an undeclared scope is not a scope, and 190 of "
            "the 326 records cite nothing."
        )
    )
    by_publisher: list[Count] = Field(
        description=(
            "Records per contact email domain, used instead of `producer` because "
            "the domain is a value the record carries. See `docs/overview.md`."
        )
    )
    by_licence_family: list[Count] = Field(
        description="Records per licence family, grouped by `licence_family()`."
    )
    by_year: list[Count] = Field(
        description=(
            "Records per publication year, oldest first, taken from `published` and "
            "falling back on `created`. Records carrying neither date are left out; "
            "years with no record are kept, at zero, so the axis stays continuous."
        )
    )
    by_link_type: list[Count] = Field(description="Links per link type.")
    records_by_link_type: list[Count] = Field(
        description=(
            "Records offering at least one link of each type. This is the one a "
            "consumer filters on: *can I download it, query it as WFS?*"
        )
    )
    top_keywords: list[Count] = Field(
        description=(
            f"Keywords shared by at least {KEYWORD_MIN_COUNT} records. The rest of "
            "the 638 keywords belong to search, not to a facet."
        )
    )

    record_facets: list[RecordFacets] = Field(
        description=(
            "The derived values of each record, in catalogue order, so a consumer "
            "filters on the same publisher and licence family the charts count."
        )
    )
    coverage: list[FieldCoverage] = Field(
        description=(
            "Coverage of every optional field, in the declaration order of the "
            "pivot model."
        )
    )
    quality: QualityStats = Field(description="What the source metadata is missing.")


def licence_family(licence: str | None) -> str:
    """Return the family a licence string belongs to.

    The mapping is deliberately a published list of substrings rather than a
    similarity measure: a reader can check why a record landed in a family, and a
    licence matching no rule is surfaced as `OTHER_LICENCE` instead of being
    quietly folded into the nearest one.

    Args:
        licence: The licence as published by the catalogue, or `None`.

    Returns:
        The family label, `UNDECLARED_LICENCE` when the record declares nothing.
    """
    if not licence:
        return UNDECLARED_LICENCE
    folded = licence.casefold()
    for needle, family in LICENCE_FAMILIES:
        if needle in folded:
            return family
    return OTHER_LICENCE


def publisher_of(record: CatalogueRecord) -> str | None:
    """Return the publisher of a record, as the domain of its contact email.

    `producer` is not used: the catalogue spells it 134 different ways for far
    fewer organisations, and normalising those spellings would mean publishing an
    editorial decision as if the catalogue had stated it. The email domain is a
    value the record actually carries, on 98.2 % of them.

    Args:
        record: The record to attribute.

    Returns:
        The lowercased domain, or `None` when the record carries no contact email.
    """
    email = record.contact_email
    if not email or "@" not in email:
        return None
    domain = email.rsplit("@", 1)[1].strip().casefold()
    return domain or None


def publication_year(record: CatalogueRecord) -> str | None:
    """Return the publication year of a record, as a four digit string.

    `published` is preferred, `created` is the fallback: only 47.2 % of the records
    carry a publication date, and using creation for the rest describes the
    catalogue better than dropping half of it. Records carrying neither are left
    out rather than bucketed as unknown, because a histogram of unknown years is
    not a year.

    Args:
        record: The record to date.

    Returns:
        The year, or `None` when the record carries no usable date.
    """
    for value in (record.published, record.created):
        if value and len(value) >= 4 and value[:4].isdigit():
            return value[:4]
    return None


def compute_stats(
    records: list[CatalogueRecord],
    source: str = "https://data.geopf.fr/csw",
) -> CatalogueStats:
    """Aggregate a pivot catalogue.

    Pure: no I/O, no network, no mutation of the records.

    Args:
        records: The pivot records to aggregate.
        source: CSW service the records were harvested from, carried through to
            the output so the statistics say what they describe.

    Returns:
        Every aggregate the overview displays.
    """
    total = len(records)

    by_type: Counter[str] = Counter()
    by_topic: Counter[str] = Counter()
    by_theme: Counter[str] = Counter()
    by_scope: Counter[str] = Counter()
    by_publisher: Counter[str] = Counter()
    by_licence: Counter[str] = Counter()
    by_year: Counter[str] = Counter()
    by_link_type: Counter[str] = Counter()
    records_by_link_type: Counter[str] = Counter()
    keywords: Counter[str] = Counter()

    urls: set[str] = set()
    links_total = 0
    links_without_name = 0
    links_without_description = 0
    records_without_links = 0
    producers: set[str] = set()
    suspected_tests: list[str] = []
    missing_title = 0
    missing_abstract = 0

    for record in records:
        by_type[record.type.value] += 1
        # A record carries several themes and categories, so these count records
        # per value and their totals are larger than the catalogue.
        by_topic.update(set(record.topic_categories))
        by_theme.update(set(record.inspire_themes))
        keywords.update(set(record.keywords))
        by_licence[licence_family(record.licence)] += 1
        if record.spatial_scope:
            by_scope[record.spatial_scope.value] += 1

        publisher = publisher_of(record)
        if publisher:
            by_publisher[publisher] += 1
        year = publication_year(record)
        if year:
            by_year[year] += 1
        if record.producer:
            producers.add(record.producer)

        if not record.links:
            records_without_links += 1
        for link in record.links:
            links_total += 1
            by_link_type[link.type.value] += 1
            urls.add(link.url)
            if not link.description:
                links_without_description += 1
            # A link is unlabelled only when neither field says anything: the
            # catalogue fills one or the other far more often than both.
            if not link.name and not link.description:
                links_without_name += 1
        records_by_link_type.update({link.type.value for link in record.links})

        if record.title is None:
            missing_title += 1
        if record.abstract is None:
            missing_abstract += 1
        if record.suspected_test:
            suspected_tests.append(record.file_identifier)

    quality = QualityStats(
        records=total,
        missing_title=missing_title,
        missing_abstract=missing_abstract,
        suspected_tests=sorted(suspected_tests),
        links_total=links_total,
        links_distinct_urls=len(urls),
        links_without_name=links_without_name,
        links_without_description=links_without_description,
        records_without_links=records_without_links,
        distinct_producers=len(producers),
        undeclared_licence=by_licence.get(UNDECLARED_LICENCE, 0),
        undeclared_access_constraint=sum(
            1 for record in records if not record.access_constraint
        ),
    )

    return CatalogueStats(
        source=source,
        count=total,
        by_type=_ranked(by_type),
        by_topic_category=_ranked(by_topic),
        by_inspire_theme=_ranked(by_theme),
        by_spatial_scope=_ranked(by_scope),
        by_publisher=_ranked(by_publisher),
        by_licence_family=_ranked(by_licence),
        by_year=_years(by_year),
        by_link_type=_ranked(by_link_type),
        records_by_link_type=_ranked(records_by_link_type),
        top_keywords=_ranked(keywords, minimum=KEYWORD_MIN_COUNT),
        record_facets=[
            RecordFacets(
                file_identifier=record.file_identifier,
                publisher=publisher_of(record),
                licence_family=licence_family(record.licence),
                year=publication_year(record),
            )
            for record in records
        ],
        coverage=_coverage(records),
        quality=quality,
    )


def coverage_markdown(stats: CatalogueStats) -> str:
    """Render the coverage of the pivot model as a markdown table.

    The documentation quotes these figures, and a quoted figure that is typed by
    hand is a figure that drifts. This is what `scripts/stats.py --format markdown`
    prints, to be pasted into `docs/model.md`.

    Args:
        stats: Aggregates of the catalogue to describe.

    Returns:
        A markdown table, newline terminated.
    """
    lines = [
        f"Measured over the {stats.count} records of the pivot catalogue.",
        "",
        "| Field | Records | Coverage |",
        "|---|---:|---:|",
    ]
    lines += [
        f"| `{item.field}` | {item.count} | {item.share:.1f} % |"
        for item in stats.coverage
    ]
    return "\n".join(lines) + "\n"


def load_records(path: Path) -> tuple[str, list[CatalogueRecord]]:
    """Read an aggregated `catalogue.json` back into the pivot model.

    Args:
        path: The catalogue written by `gpf_catalogue.parse.write_catalogue()`.

    Returns:
        The source service it declares, and its records.

    Raises:
        ValueError: If the document is not an aggregated catalogue.
    """
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or "records" not in payload:
        raise ValueError(f"{path} is not an aggregated catalogue")
    records = [CatalogueRecord.model_validate(item) for item in payload["records"]]
    logger.debug("read %d records from %s", len(records), path)
    return str(payload.get("source", "")), records


def write_stats(stats: CatalogueStats, path: Path) -> None:
    """Write the aggregates as a JSON document.

    Like `catalogue.json`, the output carries no timestamp: two runs over the same
    catalogue produce the same bytes.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        stats.model_dump_json(by_alias=True, indent=2) + "\n", encoding="utf-8"
    )
    logger.info("wrote %s (%d records)", path, stats.count)


def _ranked(counter: Counter[str], minimum: int = 1) -> list[Count]:
    """Return a counter as counts, most frequent first, ties broken alphabetically.

    The alphabetical tie break is what makes the output byte stable: `Counter`
    preserves insertion order for equal counts, which depends on the order records
    were read in.
    """
    return [
        Count(value=value, count=count)
        for value, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))
        if count >= minimum
    ]


def _years(counter: Counter[str]) -> list[Count]:
    """Return a year histogram over a continuous axis, oldest first.

    Years with no record are emitted with a count of zero rather than skipped. The
    catalogue publishes nothing between 1994 and 2008, and drawing 1994 next to
    2008 as two adjacent columns would draw a gap as if it were a step: the axis
    would no longer be time. A zero is also a true statement about that year.
    """
    if not counter:
        return []
    years = sorted(int(year) for year in counter)
    return [
        Count(value=str(year), count=counter.get(str(year), 0))
        for year in range(years[0], years[-1] + 1)
    ]


def _coverage(records: list[CatalogueRecord]) -> list[FieldCoverage]:
    """Count how often each optional field of the pivot model is filled in.

    Fields are read from the model itself rather than listed here, so that a field
    added to `CatalogueRecord` is measured without anyone remembering to add it.
    """
    total = len(records)
    coverage: list[FieldCoverage] = []
    for name, info in CatalogueRecord.model_fields.items():
        if name in _NOT_COVERAGE:
            continue
        count = sum(1 for record in records if getattr(record, name))
        coverage.append(
            FieldCoverage(
                field=info.alias or name,
                count=count,
                share=round(100 * count / total, 1) if total else 0.0,
            )
        )
    return coverage
