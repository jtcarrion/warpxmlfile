"""Helper functions: coercion, grids, params and pair series on the fixture."""

from __future__ import annotations

import numpy as np
import pytest
from conftest import FIXTURES, PER_TILT_TAGS

import xmlfile
from xmlfile import XmlElement


@pytest.fixture(scope="module")
def root():
    return xmlfile.read(FIXTURES[0].path).root


# -- text_to_list / list_to_text ------------------------------------------------


def test_text_to_list_angles_are_floats(root, fixture):
    angles = xmlfile.text_to_list(root.find("Angles"), float)
    assert len(angles) == fixture.tilts
    assert angles[0] == -40.01
    assert all(isinstance(a, float) for a in angles)


def test_text_to_list_use_tilt_are_bools(root, fixture):
    used = xmlfile.text_to_list(root.find("UseTilt"), bool)
    assert len(used) == fixture.tilts
    assert set(used) == {True}


def test_text_to_list_rejects_non_boolean():
    with pytest.raises(ValueError, match="not a boolean"):
        xmlfile.text_to_list(XmlElement("UseTilt", text="True\nyes"), bool)


def test_text_to_list_empty_element():
    assert xmlfile.text_to_list(XmlElement("Empty")) == []


def test_list_to_text_round_trips_per_tilt_fields(root):
    for tag in PER_TILT_TAGS:
        element = root.find(tag)
        text = xmlfile.list_to_text(xmlfile.text_to_list(element))
        assert text == element.text.strip()


def test_list_to_text_reproduces_warp_numbers(root):
    for tag in ("Angles", "Dose", "AxisAngle", "AxisOffsetX", "AxisOffsetY"):
        element = root.find(tag)
        values = xmlfile.text_to_list(element, float)
        assert xmlfile.list_to_text(values) == element.text.strip()


def test_list_to_text_bools_ints_and_formats():
    assert xmlfile.list_to_text([True, False]) == "True\nFalse"
    assert xmlfile.list_to_text([1, 2, 3], separator=" ") == "1 2 3"
    assert xmlfile.list_to_text([0.5, 1.0]) == "0.5\n1"
    assert xmlfile.list_to_text([2.5, 1e-7]) == "2.5\n1E-07"
    assert xmlfile.list_to_text([0.5], value_format="%.3f") == "0.500"
    assert xmlfile.list_to_text([0.5], value_format="{:.2e}") == "5.00e-01"
    assert xmlfile.list_to_text([0.5], value_format=lambda v: "x") == "x"


# -- params ---------------------------------------------------------------------


def test_params_to_dict_ctf(root, fixture):
    params = xmlfile.params_to_dict(root.find("CTF"))
    assert len(params) == fixture.ctf_params
    assert params["PixelSize"] == "0.7894"
    assert (
        len(xmlfile.params_to_dict(root.find("OptionsCTF")))
        == fixture.options_ctf_params
    )


def test_params_to_pairs_preserves_order(root):
    pairs = xmlfile.params_to_pairs(root.find("CTF"))
    assert [name for name, _ in pairs] == [p.get("Name") for p in root.find("CTF")]


def test_params_duplicates():
    block = XmlElement(
        "CTF",
        children=[
            XmlElement("Param", {"Name": "A", "Value": "1"}),
            XmlElement("Param", {"Name": "A", "Value": "2"}),
        ],
    )
    with pytest.raises(ValueError, match="duplicate"):
        xmlfile.params_to_dict(block)
    assert xmlfile.params_to_dict(block, allow_duplicates=True) == {"A": "2"}
    assert xmlfile.params_to_pairs(block) == [("A", "1"), ("A", "2")]


def test_params_missing_attribute():
    block = XmlElement("CTF", children=[XmlElement("Param", {"Name": "A"})])
    with pytest.raises(ValueError, match="without Name and Value"):
        xmlfile.params_to_pairs(block)


# -- grids ----------------------------------------------------------------------


def test_grid_to_array_3d(root, fixture):
    element = root.find("GridMovementX")
    values = xmlfile.grid_to_array(element)
    assert values.shape == (41, 4, 6)
    assert values.dtype == np.float32
    assert values.size == fixture.grid_movement_x_nodes
    nodes = element.findall("Node")
    assert values[0, 0, 0] == np.float32(nodes[0].get("Value"))
    node = next(
        n for n in nodes if (n.get("X"), n.get("Y"), n.get("Z")) == ("5", "0", "34")
    )
    assert values[34, 0, 5] == np.float32(node.get("Value"))
    assert values.ravel()[5] == np.float32(nodes[5].get("Value"))
    assert xmlfile.grid_margins(element) == (0.0, 0.0, 0.0)


def test_grid_to_array_4d(root, fixture):
    element = root.find("GridVolumeWarpX")
    values = xmlfile.grid_to_array(element)
    assert values.shape == (41, 1, 6, 4)
    assert values.size == fixture.grid_volume_warp_x_nodes
    assert xmlfile.grid_margins(element) == ()


def test_grid_to_array_single_node(root):
    assert xmlfile.grid_to_array(root.find("GridLocationBfacs")).shape == (1, 1, 1)


def _grid(nodes: list[tuple[int, int, int, str]], **sizes) -> XmlElement:
    attributes = {"Width": "2", "Height": "1", "Depth": "1", **sizes}
    return XmlElement(
        "G",
        attributes,
        children=[
            XmlElement("Node", {"X": str(x), "Y": str(y), "Z": str(z), "Value": v})
            for x, y, z, v in nodes
        ],
    )


def test_grid_to_array_errors():
    with pytest.raises(ValueError, match="1 Node children, expected 2"):
        xmlfile.grid_to_array(_grid([(0, 0, 0, "1")]))
    with pytest.raises(ValueError, match="appears twice"):
        xmlfile.grid_to_array(_grid([(0, 0, 0, "1"), (0, 0, 0, "2")]))
    with pytest.raises(ValueError, match="out of range"):
        xmlfile.grid_to_array(_grid([(0, 0, 0, "1"), (2, 0, 0, "2")]))


def test_array_to_grid_reproduces_every_fixture_grid(root):
    grids = [child for child in root if child.tag.startswith("Grid")]
    assert len(grids) == 18
    for element in grids:
        rebuilt = xmlfile.array_to_grid(
            xmlfile.grid_to_array(element),
            element.tag,
            margins=xmlfile.grid_margins(element),
            template=element,
        )
        assert rebuilt == element, element.tag


def test_array_to_grid_round_trip_random():
    rng = np.random.default_rng(0)
    for shape in ((3, 2, 4), (2, 3, 2, 4)):
        values = rng.standard_normal(shape).astype(np.float32) * 1e3
        element = xmlfile.array_to_grid(values, "G", margins=(0,) * len(shape))
        parsed = xmlfile.from_string(xmlfile.to_string(xmlfile.XmlDocument(element)))
        np.testing.assert_array_equal(xmlfile.grid_to_array(parsed.root), values)
        assert xmlfile.grid_margins(parsed.root) == (0.0,) * len(shape)


def test_array_to_grid_layout_without_template():
    element = xmlfile.array_to_grid(np.zeros((1, 1, 2), dtype=np.float32), "G")
    assert element.attributes == {"Width": "2", "Height": "1", "Depth": "1"}
    assert [n.attributes for n in element] == [
        {"X": "0", "Y": "0", "Z": "0", "Value": "0"},
        {"X": "1", "Y": "0", "Z": "0", "Value": "0"},
    ]
    assert xmlfile.to_string(xmlfile.XmlDocument(element)) == (
        '<G Width="2" Height="1" Depth="1">\n\t\t'
        '<Node X="0" Y="0" Z="0" Value="0" />\n\t\t'
        '<Node X="1" Y="0" Z="0" Value="0" />\n\t</G>'
    )
    four_d = xmlfile.array_to_grid(np.zeros((2, 1, 1, 1)), "G")
    assert four_d.attributes == {
        "Width": "1",
        "Height": "1",
        "Depth": "1",
        "Duration": "2",
    }
    assert four_d[1].attributes == {
        "X": "0",
        "Y": "0",
        "Z": "0",
        "W": "1",
        "Value": "0",
    }


def test_array_to_grid_errors():
    with pytest.raises(ValueError, match="3-D or 4-D"):
        xmlfile.array_to_grid(np.zeros((2, 2)), "G")
    with pytest.raises(ValueError, match="margins"):
        xmlfile.array_to_grid(np.zeros((1, 1, 1)), "G", margins=(0, 0))


def test_replace_grid_in_place_changes_only_that_element(xml_path, tmp_path):
    doc = xmlfile.read(xml_path)
    old = doc.root.find("GridMovementX")
    values = xmlfile.grid_to_array(old) + np.float32(1.5)
    new = xmlfile.array_to_grid(
        values, old.tag, margins=xmlfile.grid_margins(old), template=old
    )
    doc.root.children[doc.root.children.index(old)] = new
    out = tmp_path / "edited.xml"
    xmlfile.write(doc, out)

    original_lines = xml_path.read_text(encoding="utf-8").splitlines()
    edited_lines = out.read_text(encoding="utf-8").splitlines()
    assert len(original_lines) == len(edited_lines)
    changed = [
        i
        for i, (a, b) in enumerate(zip(original_lines, edited_lines, strict=True))
        if a != b
    ]
    assert len(changed) == values.size
    assert all("<Node " in edited_lines[i] for i in changed)
    reread = xmlfile.read(out).root.find("GridMovementX")
    np.testing.assert_array_equal(xmlfile.grid_to_array(reread), values)


# -- pair series ----------------------------------------------------------------


def test_parse_pair_series(root, fixture):
    series = root.findall("TiltPS1D")
    assert len(series) == fixture.tilts
    values = xmlfile.parse_pair_series(series[0])
    assert values.shape == (256, 2)
    assert values[0, 0] == 0.0
    assert values[1, 0] == 0.001953125


def test_pair_series_round_trips_every_tilt(root):
    for element in root.findall("TiltPS1D") + root.findall("TiltSimulatedScale"):
        values = xmlfile.parse_pair_series(element)
        assert xmlfile.pair_series_to_text(values) == element.text.strip()


def test_pair_series_errors_and_empty():
    assert xmlfile.parse_pair_series(XmlElement("S")).shape == (0, 2)
    with pytest.raises(ValueError, match="not an x\\|y pair"):
        xmlfile.parse_pair_series(XmlElement("S", text="1|2;3"))
    with pytest.raises(ValueError, match=r"shape \(n, 2\)"):
        xmlfile.pair_series_to_text(np.zeros(3))
