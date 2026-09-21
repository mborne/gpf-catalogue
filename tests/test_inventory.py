"""Tests of what the three services say they serve.

Offline, like `test_parse.py`: `parse_inventory()` takes bytes. The samples of
`tests/data/` are trimmed from the live responses and keep one example of every
shape that matters — a padded title, an entry with no name, and the identifiers a
WMTS gives to things that are not layers.
"""
# Author: Claude (Anthropic) — this file is AI generated, see docs/init.md.

import pytest

from gpf_catalogue.inventory import parse_inventory, read_inventories, resource_key
from gpf_catalogue.storage import service_page_path


def test_wfs_feature_types_are_keyed_by_their_type_name(sample):
    """`wfs:Name` is the `typeName`, which is what a record publishes as link name."""
    inventory = parse_inventory("wfs", [sample("wfs-capabilities.xml")])

    assert inventory.service == "wfs"
    assert inventory.keys == {
        "BDTOPO_V3:batiment",
        "OCS-GERS_BDD_LAMB93_2016:oscge_gers_32_2016",
    }


def test_a_feature_type_without_a_name_is_dropped(sample):
    """Nothing can be matched against it, so counting it would only inflate the total."""
    inventory = parse_inventory("wfs", [sample("wfs-capabilities.xml")])

    assert len(inventory.resources) == 2
    assert all(resource.key for resource in inventory.resources)


def test_titles_are_stripped(sample):
    """The live service pads them — " OCSGE Gers 2016 " — and a diff is not whitespace."""
    inventory = parse_inventory("wfs", [sample("wfs-capabilities.xml")])
    titles = {resource.key: resource.title for resource in inventory.resources}

    assert titles["OCS-GERS_BDD_LAMB93_2016:oscge_gers_32_2016"] == "OCSGE Gers 2016"


def test_only_a_wmts_layer_is_a_wmts_layer(sample):
    """Styles and tile matrix sets carry an `ows:Identifier` too.

    The live capabilities holds 2 292 of them for 712 layers, so a `.//` path would
    report three resources out of four that no record could ever describe.
    """
    inventory = parse_inventory("wmts", [sample("wmts-capabilities.xml")])

    assert inventory.keys == {"ACCES.BIOMETHANE", "ORTHOIMAGERY.ORTHOPHOTOS"}
    assert "normal" not in inventory.keys
    assert "PM" not in inventory.keys


def test_the_download_feed_is_read_across_its_pages(sample):
    """It is an Atom feed of ten entries a page, not a single capabilities document."""
    inventory = parse_inventory(
        "download",
        [sample("download-feed-01.xml"), sample("download-feed-02.xml")],
    )

    assert inventory.keys == {"ADMIN-EXPRESS", "ACCESSIBILITE-PHYSIQUE-FORETS", "BDTOPO"}


def test_a_download_resource_is_keyed_by_its_url_not_its_title(sample):
    """The id is the URL a record publishes, which is what makes the match a match."""
    inventory = parse_inventory("download", [sample("download-feed-01.xml")])
    first = inventory.resources[0]

    assert first.key == "ADMIN-EXPRESS"
    assert first.title == "ADMIN-EXPRESS"


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://data.geopf.fr/telechargement/resource/ENR", "ENR"),
        ("https://data.geopf.fr/telechargement/resource/ENR/", "ENR"),
        # A file inside a delivery names no resource: it says which archive to
        # fetch, not which of the 116 resources the record describes.
        (
            "https://data.geopf.fr/telechargement/download/ENR/ENR_1-0/ENR_1-0.7z",
            None,
        ),
        ("https://data.geopf.fr/annexes/ressources/documentation/BDForet.gpkg", None),
        ("https://data.geopf.fr/telechargement/resource/", None),
    ],
)
def test_only_a_resource_url_is_a_download_claim(url, expected):
    assert resource_key(url) == expected


def test_an_unknown_service_is_refused(sample):
    with pytest.raises(ValueError, match="unknown service"):
        parse_inventory("wcs", [sample("wfs-capabilities.xml")])


def test_a_service_that_was_never_harvested_is_missing_not_empty(sample, tmp_path):
    """An empty inventory would say the service serves nothing.

    Every record citing it would then be reported as citing something that does not
    exist, which is a statement about this pipeline and not about the catalogue.
    """
    service_page_path(tmp_path, "wfs", 1).write_bytes(sample("wfs-capabilities.xml"))

    inventories, missing = read_inventories(tmp_path)

    assert [inventory.service for inventory in inventories] == ["wfs"]
    assert missing == ["wmts", "download"]


def test_the_pages_of_one_inventory_are_read_in_order(sample, tmp_path):
    """Page 10 must not sort before page 2; the numbers are zero padded for that."""
    for page in (1, 2):
        service_page_path(tmp_path, "download", page).write_bytes(
            sample(f"download-feed-{page:02d}.xml")
        )

    inventories, _ = read_inventories(tmp_path, ["download"])

    keys = [resource.key for resource in inventories[0].resources]
    assert keys == ["ADMIN-EXPRESS", "ACCESSIBILITE-PHYSIQUE-FORETS", "BDTOPO"]
