"""Tests of the conversion from ISO 19115-3 to the pivot model.

They run offline on the sample records of `tests/data`, which cover the shapes met
in the Géoplateforme catalogue: a dataset, a real service record with English
translations, a record without title, and a title carried by an anchor.
"""
# Author: Claude (Anthropic) — this file is AI generated, see docs/init.md.

import pytest

from gpf_catalogue.model import ResourceType
from gpf_catalogue.parse import ParseError, parse_record


def test_dataset(sample):
    """A dataset record yields its identifier, title and abstract."""
    record = parse_record(sample("dataset.xml"))

    assert record.file_identifier == "SAMPLE_DATASET"
    assert record.type is ResourceType.DATASET
    assert record.title == "Sample dataset"
    assert record.abstract == "A sample dataset used by the tests."


def test_nested_citation_is_not_the_title(sample):
    """Thesaurus citations must not be mistaken for the resource title."""
    record = parse_record(sample("dataset.xml"))

    assert record.title != "A thesaurus, not the title"


def test_service(sample):
    """A real service record is read through the same paths as a dataset."""
    record = parse_record(sample("GeoPF_Altimetrie.xml"))

    assert record.file_identifier == "GeoPF_Altimetrie"
    assert record.type is ResourceType.SERVICE
    assert record.title == "API Géoplateforme - Calcul altimétrique"
    assert record.abstract is not None


def test_default_locale_wins_over_translation(sample):
    """The default locale value is preferred over a `lan:PT_FreeText` translation."""
    record = parse_record(sample("GeoPF_Altimetrie.xml"))

    assert "Geoplatform API" not in record.title


def test_record_without_title(sample):
    """A record without title is kept, with a null title rather than a guess."""
    record = parse_record(sample("no-title.xml"))

    assert record.file_identifier == "SAMPLE_NO_TITLE"
    assert record.type is ResourceType.SERIES
    assert record.title is None
    assert record.abstract is None


def test_title_from_anchor_and_inferred_type(sample):
    """A `gcx:Anchor` carries the title, and the type falls back on the block type."""
    record = parse_record(sample("anchor-no-scope.xml"))

    assert record.title == "Anchored title"
    assert record.type is ResourceType.SERVICE
    # An element holding only whitespace is an absent value, not an empty one.
    assert record.abstract is None


def test_invalid_xml():
    """A malformed document is reported, not propagated as an XML error."""
    with pytest.raises(ParseError):
        parse_record(b"<not-xml")


def test_document_without_metadata():
    """A well formed document that is not an ISO record is reported."""
    with pytest.raises(ParseError, match="MD_Metadata"):
        parse_record(b"<html><body>not a metadata record</body></html>")


def test_json_uses_iso_field_names(sample):
    """The JSON written to disk keeps the ISO flavoured field names."""
    record = parse_record(sample("dataset.xml"))

    assert record.model_dump(by_alias=True) == {
        "fileIdentifier": "SAMPLE_DATASET",
        "type": "dataset",
        "title": "Sample dataset",
        "abstract": "A sample dataset used by the tests.",
    }
