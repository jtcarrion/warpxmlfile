"""Test category 2: round-tripping through a string.

Two guarantees are tested:

* semantic identity - the parsed document survives to_string/from_string
  unchanged, in both the whitespace-preserving and semantic modes;
* byte identity - a file read and serialised with the defaults reproduces the
  original bytes exactly, including the BOM, tab indentation and the absent
  trailing newline.
"""

from __future__ import annotations

import xmlfile


def test_semantic_round_trip_preserving_whitespace(xml_path):
    original = xmlfile.read(xml_path)
    copy = xmlfile.from_string(xmlfile.to_string(original))
    assert copy == original


def test_semantic_round_trip_without_whitespace(xml_path):
    original = xmlfile.read(xml_path, preserve_whitespace=False)
    text = xmlfile.to_string(original, indent="  ")
    copy = xmlfile.from_string(text, preserve_whitespace=False)
    assert copy == original


def test_byte_exact_round_trip(xml_path):
    doc = xmlfile.read(xml_path)
    assert xmlfile.to_string(doc) == xml_path.read_text(encoding="utf-8")


def test_pretty_printing_is_idempotent(xml_path):
    doc = xmlfile.read(xml_path, preserve_whitespace=False)
    once = xmlfile.to_string(doc, indent="  ")
    twice = xmlfile.to_string(
        xmlfile.from_string(once, preserve_whitespace=False), indent="  "
    )
    assert once == twice


def test_round_trip_preserves_root_attribute_order(xml_path):
    original = xmlfile.read(xml_path)
    copy = xmlfile.from_string(xmlfile.to_string(original))
    assert list(copy.root.attributes) == list(original.root.attributes)


def test_round_trip_preserves_repeated_element_order(xml_path):
    original = xmlfile.read(xml_path)
    copy = xmlfile.from_string(xmlfile.to_string(original))
    assert [e.get("ID") for e in copy.root.findall("TiltPS1D")] == [
        e.get("ID") for e in original.root.findall("TiltPS1D")
    ]


def test_round_trip_preserves_grid_node_order(xml_path):
    original = xmlfile.read(xml_path).root.find("GridMovementX")
    copy = xmlfile.from_string(xmlfile.to_string(xmlfile.read(xml_path))).root.find(
        "GridMovementX"
    )
    assert [n.attributes for n in copy.children] == [
        n.attributes for n in original.children
    ]


def test_round_trip_does_not_reformat_numeric_text(xml_path):
    original = xmlfile.read(xml_path)
    copy = xmlfile.from_string(xmlfile.to_string(original))
    for tag in ("Angles", "Dose", "AxisOffsetX"):
        assert copy.root.find(tag).text == original.root.find(tag).text


def test_pretty_printing_does_not_reformat_significant_text(xml_path):
    """Re-indenting must not touch the newline-separated per-tilt blocks."""
    doc = xmlfile.read(xml_path, preserve_whitespace=False)
    copy = xmlfile.from_string(
        xmlfile.to_string(doc, indent="  "), preserve_whitespace=False
    )
    assert copy.root.find("Angles").text == doc.root.find("Angles").text
    assert copy.root.find("MoviePath").text == doc.root.find("MoviePath").text
