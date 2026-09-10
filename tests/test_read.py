"""Test category 1: basic read."""

from __future__ import annotations

import re

import xmlfile
from conftest import PER_TILT_TAGS, Fixture, count_lines


def test_root_tag(xml_path):
    assert xmlfile.read(xml_path).root.tag == "TiltSeries"


def test_root_attribute_count(fixture: Fixture):
    doc = xmlfile.read(fixture.path)
    assert len(doc.root.attributes) == fixture.root_attributes


def test_root_attribute_order_matches_the_file(xml_path):
    doc = xmlfile.read(xml_path)
    names = list(doc.root.attributes)

    raw = xml_path.read_text(encoding="utf-8")
    start_tag = re.search(r"<TiltSeries\s[^>]*>", raw).group(0)
    names_in_file = re.findall(r'([A-Za-z0-9_]+)="', start_tag)

    assert names == names_in_file
    assert names != sorted(names), "attributes must not be alphabetised"


def test_child_element_count(fixture: Fixture):
    doc = xmlfile.read(fixture.path)
    assert len(doc.root.children) == fixture.children


def test_child_order_is_preserved(xml_path):
    doc = xmlfile.read(xml_path)
    tags = [child.tag for child in doc.root.children]
    assert tags[:5] == ["Angles", "Dose", "UseTilt", "AxisAngle", "AxisOffsetX"]
    assert tags[-1] == "GridLocationWeights"


def test_per_tilt_fields_all_have_the_same_length(fixture: Fixture):
    doc = xmlfile.read(fixture.path)
    for tag in PER_TILT_TAGS:
        element = doc.root.find(tag)
        assert element is not None, f"{tag} missing from {fixture.name}"
        assert count_lines(element.text) == fixture.tilts, tag


def test_repeated_tags_are_preserved(fixture: Fixture):
    doc = xmlfile.read(fixture.path)
    assert len(doc.root.findall("TiltPS1D")) == fixture.tilts
    assert len(doc.root.findall("TiltSimulatedScale")) == fixture.tilts


def test_repeated_tag_order_is_preserved(xml_path):
    doc = xmlfile.read(xml_path)
    ids = [element.get("ID") for element in doc.root.findall("TiltPS1D")]
    assert ids == [str(i) for i in range(len(ids))]


def test_nested_param_blocks(fixture: Fixture):
    doc = xmlfile.read(fixture.path)
    ctf = doc.root.find("CTF")
    assert ctf is not None
    assert len(ctf.findall("Param")) == fixture.ctf_params

    options_ctf = doc.root.find("OptionsCTF")
    assert options_ctf is not None
    assert len(options_ctf.findall("Param")) == fixture.options_ctf_params


def test_grid_node_counts_match_declared_dimensions(fixture: Fixture):
    doc = xmlfile.read(fixture.path)

    movement = doc.root.find("GridMovementX")
    assert movement is not None
    assert len(movement.children) == fixture.grid_movement_x_nodes
    expected = (
        int(movement.get("Width"))
        * int(movement.get("Height"))
        * int(movement.get("Depth"))
    )
    assert len(movement.children) == expected

    warp = doc.root.find("GridVolumeWarpX")
    assert warp is not None
    assert len(warp.children) == fixture.grid_volume_warp_x_nodes
    expected = (
        int(warp.get("Width"))
        * int(warp.get("Height"))
        * int(warp.get("Depth"))
        * int(warp.get("Duration"))
    )
    assert len(warp.children) == expected


def test_values_are_not_coerced(xml_path):
    """The base parser stores strings, never numbers or booleans."""
    doc = xmlfile.read(xml_path)
    for element in doc.root.iter():
        for value in element.attributes.values():
            assert isinstance(value, str)
        assert element.text is None or isinstance(element.text, str)

    use_tilt = doc.root.find("UseTilt")
    assert use_tilt.text.split("\n")[0] == "True"  # not Python's True


def test_numeric_text_keeps_its_exact_formatting(xml_path):
    """Trailing zeros and exponent style must survive reading."""
    doc = xmlfile.read(xml_path)
    raw = xml_path.read_text(encoding="utf-8")
    angles = doc.root.find("Angles").text
    assert angles in raw


def test_declaration_and_byte_order_mark(xml_path):
    doc = xmlfile.read(xml_path)
    assert doc.declaration is not None
    assert doc.declaration.version == "1.0"
    assert doc.declaration.encoding == "utf-8"
    assert doc.byte_order_mark is True


def test_filename_is_recorded(xml_path):
    assert xmlfile.read(xml_path).filename == xml_path
