"""Tests of the comparison between the catalogue and what the services serve.

Pure, like `test_stats.py`: `compute_coverage()` takes records and inventories. The
records are built by hand so that each test states exactly the shape it is about,
and the inventories are read from the samples of `tests/data/`.
"""
# Author: Claude (Anthropic) — this file is AI generated, see docs/init.md.

import json

import pytest

from gpf_catalogue.coverage import (
    MAX_CITING_RECORDS,
    claimed_keys,
    compute_coverage,
    coverage_markdown,
    write_coverage,
)
from gpf_catalogue.inventory import parse_inventory
from gpf_catalogue.model import CatalogueRecord, Link, LinkType, ResourceType


def record(identifier: str = "R", **fields) -> CatalogueRecord:
    """Build a pivot record, defaulting everything the test does not care about."""
    fields.setdefault("type", ResourceType.DATASET)
    return CatalogueRecord(file_identifier=identifier, **fields)


def wfs(name: str | None, url: str = "https://data.geopf.fr/wfs/ows") -> Link:
    """A WFS link naming one feature type, the way the catalogue publishes them."""
    return Link(type=LinkType.WFS, url=url, name=name)


@pytest.fixture
def inventory(sample):
    """The WFS inventory of the samples: two feature types."""
    return parse_inventory(
        "wfs", [sample("wfs-capabilities.xml")], endpoint="https://data.geopf.fr/wfs"
    )


def test_a_described_feature_type_is_covered(inventory):
    records = [record("A", links=[wfs("BDTOPO_V3:batiment")])]

    service = compute_coverage(records, [inventory]).services[0]

    assert service.published == 2
    assert service.covered == 1
    assert service.records == 1
    assert service.endpoint == "https://data.geopf.fr/wfs"


def test_what_no_record_describes_is_listed_not_only_counted(inventory):
    """The list is the actionable half: a count says how many, not which ones."""
    records = [record("A", links=[wfs("BDTOPO_V3:batiment")])]

    service = compute_coverage(records, [inventory]).services[0]

    assert [resource.key for resource in service.uncovered] == [
        "OCS-GERS_BDD_LAMB93_2016:oscge_gers_32_2016"
    ]
    # The title comes with it, because a `typeName` alone says little.
    assert service.uncovered[0].title == "OCSGE Gers 2016"


def test_uncovered_keeps_the_order_the_service_published(sample):
    """A capabilities groups related layers; that grouping is a reading aid."""
    empty = compute_coverage([], [parse_inventory("wfs", [sample("wfs-capabilities.xml")])])

    assert [resource.key for resource in empty.services[0].uncovered] == [
        "BDTOPO_V3:batiment",
        "OCS-GERS_BDD_LAMB93_2016:oscge_gers_32_2016",
    ]


def test_a_record_citing_something_the_service_does_not_serve_is_reported(inventory):
    """A withdrawn layer, a stale record, or an endpoint outside the public service."""
    records = [record("A", links=[wfs("BDTOPO_V3:withdrawn")])]

    service = compute_coverage(records, [inventory]).services[0]

    assert [claim.key for claim in service.unknown] == ["BDTOPO_V3:withdrawn"]
    assert service.unknown[0].records == ["A"]
    assert service.unknown[0].citing == 1
    assert service.covered == 0


def test_an_unknown_claim_names_the_records_that_made_it(inventory):
    """It has to be traceable: the point is to open the record and fix it."""
    records = [
        record(f"R{index}", links=[wfs("BDTOPO_V3:withdrawn")])
        for index in range(MAX_CITING_RECORDS + 5)
    ]

    claim = compute_coverage(records, [inventory]).services[0].unknown[0]

    assert claim.citing == MAX_CITING_RECORDS + 5
    # Truncated: past a handful the claim is a pattern, not a record to open.
    assert len(claim.records) == MAX_CITING_RECORDS


def test_the_same_layer_described_by_two_records_is_covered_once(inventory):
    """`IGNF_ADMIN-EXPRESS` publishes 251 link entries; coverage counts layers."""
    records = [
        record("A", links=[wfs("BDTOPO_V3:batiment"), wfs("BDTOPO_V3:batiment")]),
        record("B", links=[wfs("BDTOPO_V3:batiment")]),
    ]

    service = compute_coverage(records, [inventory]).services[0]

    assert service.covered == 1
    assert service.claimed == 1
    assert service.links == 3
    assert service.records == 2


def test_a_link_with_nothing_to_match_on_is_counted_as_such(inventory):
    """One of the 657 WFS links of the catalogue carries no `cit:name` at all."""
    records = [record("A", links=[wfs(None), wfs("BDTOPO_V3:batiment")])]

    service = compute_coverage(records, [inventory]).services[0]

    assert service.links == 2
    assert service.links_without_key == 1
    assert service.claimed == 1


def test_a_download_claim_is_read_from_the_url(sample):
    """A download link carries a URL, not a layer, so the key is in the path."""
    inventory = parse_inventory(
        "download", [sample("download-feed-01.xml"), sample("download-feed-02.xml")]
    )
    records = [
        record(
            "A",
            links=[
                Link(
                    type=LinkType.DOWNLOAD,
                    url="https://data.geopf.fr/telechargement/resource/BDTOPO",
                ),
                # Straight at a file inside a delivery: it names no resource, so it
                # is neither a claim nor an anomaly.
                Link(
                    type=LinkType.DOWNLOAD,
                    url="https://data.geopf.fr/telechargement/download/BDTOPO/x.7z",
                ),
            ],
        )
    ]

    service = compute_coverage(records, [inventory]).services[0]

    assert service.covered == 1
    assert service.unknown == []
    assert service.links == 2
    assert service.links_without_key == 1


def test_links_of_another_service_are_not_counted(inventory):
    """A WMS link says nothing about the WFS, whatever its name looks like."""
    records = [
        record(
            "A",
            links=[
                Link(
                    type=LinkType.WMS,
                    url="https://data.geopf.fr/wms-v/ows",
                    name="BDTOPO_V3:batiment",
                )
            ],
        )
    ]

    service = compute_coverage(records, [inventory]).services[0]

    assert service.claimed == 0
    assert service.links == 0
    assert service.covered == 0


def test_claims_are_readable_on_their_own(inventory):
    """`claimed_keys()` is what the rule *is*; the coverage is what it is used for."""
    records = [record("A", links=[wfs(" BDTOPO_V3:batiment ")])]

    assert claimed_keys(records, "wfs") == {"BDTOPO_V3:batiment": ["A"]}
    with pytest.raises(ValueError, match="unknown service"):
        claimed_keys(records, "wcs")


def test_a_service_with_no_inventory_is_absent_rather_than_empty(inventory):
    """Two measured services beat three, one of which is wrong."""
    coverage = compute_coverage([], [inventory])

    assert [service.service for service in coverage.services] == ["wfs"]


def test_the_markdown_table_is_what_the_documentation_quotes(inventory):
    table = coverage_markdown(compute_coverage([], [inventory]))

    assert "| Service | Published |" in table
    assert "| `wfs` (feature types) | 2 | 0 | 0.0 % | 2 | 0 |" in table


def test_two_runs_write_the_same_bytes(inventory, tmp_path):
    """No timestamp, like `catalogue.json` and `stats.json`: a diff is a change."""
    records = [record("A", links=[wfs("BDTOPO_V3:batiment")])]
    coverage = compute_coverage(records, [inventory])

    write_coverage(coverage, tmp_path / "first.json")
    write_coverage(compute_coverage(records, [inventory]), tmp_path / "second.json")

    assert (tmp_path / "first.json").read_bytes() == (tmp_path / "second.json").read_bytes()
    assert json.loads((tmp_path / "first.json").read_text(encoding="utf-8"))["records"] == 1
