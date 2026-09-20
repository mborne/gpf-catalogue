"""Tests of the identifier to file name rules.

Every case below comes from an identifier actually published by the Géoplateforme
catalogue.
"""
# Author: Claude (Anthropic) — this file is AI generated, see docs/init.md.

import pytest

from gpf_catalogue.storage import (
    build_filename_map,
    json_path,
    safe_filename,
    stem_of,
    xml_path,
)


def test_usual_identifier_is_left_untouched():
    """Most identifiers are already safe and must stay readable."""
    assert safe_filename("IGNF_BD-TOPO") == "IGNF_BD-TOPO"


def test_spaces_and_accents_are_encoded():
    """`Métropole du Grand Paris - Trame noire` is a real identifier."""
    assert (
        safe_filename("Métropole du Grand Paris - Trame noire")
        == "M%C3%A9tropole%20du%20Grand%20Paris%20-%20Trame%20noire"
    )


def test_path_separators_cannot_escape(tmp_path):
    """An identifier cannot be turned into a path traversal."""
    # Separators are encoded, and a leading dot is prefixed so that no record is
    # ever written as a hidden file.
    assert safe_filename("../../etc/passwd") == "_..%2F..%2Fetc%2Fpasswd"
    with pytest.raises(ValueError):
        xml_path(tmp_path, "../escaped")


def test_empty_identifier_is_refused():
    with pytest.raises(ValueError):
        safe_filename("   ")


def test_identifier_already_ending_with_xml(tmp_path):
    """Nine identifiers end with `.xml`, which must not be swallowed."""
    path = xml_path(tmp_path, safe_filename("BDML_DELMAR.xml"))

    assert path.name == "BDML_DELMAR.xml.xml"
    assert stem_of(path) == "BDML_DELMAR.xml"


def test_identifier_looking_like_a_version(tmp_path):
    """`1.0` is a real identifier; `Path.with_suffix()` would turn it into `1`."""
    path = json_path(tmp_path, safe_filename("1.0"))

    assert path.name == "1.0.json"
    assert stem_of(path) == "1.0"


def test_case_only_collisions_are_disambiguated():
    """`id`/`ID` and `test`/`TEST` would overwrite each other on macOS or Windows."""
    stems = build_filename_map(["IGNF_BD-TOPO", "id", "ID", "test", "TEST"])

    assert stems["IGNF_BD-TOPO"] == "IGNF_BD-TOPO"
    assert stems["id"] != stems["ID"]
    assert stems["id"].startswith("id-")
    assert stems["ID"].startswith("ID-")
    assert len({stem.casefold() for stem in stems.values()}) == 5


def test_filename_map_ignores_duplicates():
    """A duplicated identifier must not be mistaken for a collision."""
    stems = build_filename_map(["one", "one", "two"])

    assert stems == {"one": "one", "two": "two"}


def test_filename_map_is_order_independent():
    """The name of a record does not depend on the order of the catalogue."""
    forward = build_filename_map(["id", "ID"])
    backward = build_filename_map(["ID", "id"])

    assert forward == backward
