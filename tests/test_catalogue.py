"""Tests of the conversion run and of the aggregated catalogue.

Unlike `test_parse.py`, these touch the file system, so they work in `tmp_path`
over copies of the sample records.
"""
# Author: Claude (Anthropic) — this file is AI generated, see docs/init.md.

import json

import pytest

from gpf_catalogue.parse import parse_all


@pytest.fixture
def mirror(tmp_path, sample):
    """A `data/csw` like directory holding three sample records."""
    data_dir = tmp_path / "csw"
    data_dir.mkdir()
    for name in ("dataset.xml", "no-title.xml", "test-record.xml"):
        (data_dir / name).write_bytes(sample(name))
    return data_dir


def _catalogue(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_one_json_per_record(mirror):
    """Each harvested record gets its pivot counterpart next to it."""
    report = parse_all(mirror)

    assert report.total == 3
    assert report.written == 3
    assert not report.failed
    assert (mirror / "dataset.json").exists()


def test_catalogue_is_written_beside_the_mirror(mirror):
    """The aggregate lands outside `data_dir`, where no record can collide with it.

    A record identified `catalogue` would otherwise be written to the very same
    path as the aggregate.
    """
    parse_all(mirror)

    assert (mirror.parent / "catalogue.json").exists()
    assert not (mirror / "catalogue.json").exists()


def test_catalogue_carries_its_source_and_every_record(mirror):
    parse_all(mirror)
    payload = _catalogue(mirror.parent / "catalogue.json")

    assert payload["source"] == "https://data.geopf.fr/csw"
    assert payload["count"] == 3
    assert len(payload["records"]) == 3
    assert {record["fileIdentifier"] for record in payload["records"]} == {
        "SAMPLE_DATASET",
        "SAMPLE_NO_TITLE",
        "SAMPLE_TEST",
    }


def test_catalogue_is_byte_stable_across_runs(mirror):
    """Two runs over the same mirror produce the same bytes.

    The aggregate carries no timestamp on purpose, so that catalogue drift can be
    diffed between two harvests (ROADMAP phase 4).
    """
    parse_all(mirror)
    first = (mirror.parent / "catalogue.json").read_bytes()
    parse_all(mirror)

    assert (mirror.parent / "catalogue.json").read_bytes() == first


def test_catalogue_path_can_be_chosen(mirror, tmp_path):
    target = tmp_path / "elsewhere" / "cat.json"
    parse_all(mirror, catalogue_path=target)

    assert _catalogue(target)["count"] == 3


def test_report_counts_coverage_and_links(mirror):
    """The run reports what the catalogue actually carries, field by field."""
    report = parse_all(mirror)

    # Only the dataset sample carries these.
    assert report.coverage["producer"] == 1
    assert report.coverage["bbox"] == 1
    assert report.coverage["links"] == 1
    assert report.links_by_type["wfs"] == 1
    # Two of the three samples have no abstract worth the name, one has none.
    assert report.missing_abstract == 1


def test_report_lists_suspected_test_records(mirror):
    """Test records are named in the report, not silently dropped."""
    report = parse_all(mirror)

    assert report.suspected_tests == ["SAMPLE_TEST"]
    # They are still written: the consumer decides whether to skip them.
    assert (mirror / "test-record.json").exists()


def test_unparsable_record_is_reported_and_does_not_abort(mirror):
    """One broken record must not cost the other 332."""
    (mirror / "broken.xml").write_bytes(b"<html>not a record</html>")

    report = parse_all(mirror)

    assert report.total == 4
    assert report.written == 3
    assert [name for name, _ in report.failed] == ["broken.xml"]
    assert _catalogue(mirror.parent / "catalogue.json")["count"] == 3
