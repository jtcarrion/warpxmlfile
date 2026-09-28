"""Behaviour of the passive containers themselves."""

from __future__ import annotations

from pathlib import Path

from warpxmlfile import _xml as xmlfile
from warpxmlfile._xml import XmlDeclaration, XmlDocument, XmlElement


def test_element_defaults_are_independent():
    a = XmlElement("a")
    b = XmlElement("b")
    a.children.append(XmlElement("child"))
    a.attributes["x"] = "1"
    assert b.children == []
    assert b.attributes == {}


def test_element_equality_is_structural():
    a = XmlElement("a", {"x": "1"}, text="hello")
    b = XmlElement("a", {"x": "1"}, text="hello")
    assert a == b
    assert a != XmlElement("a", {"x": "2"}, text="hello")


def test_element_equality_is_attribute_order_sensitive():
    """Dicts compare equal regardless of order, so order is checked directly."""
    a = XmlElement("a", {"x": "1", "y": "2"})
    b = XmlElement("a", {"y": "2", "x": "1"})
    assert a == b
    assert list(a.attributes) != list(b.attributes)


def test_find_returns_first_match_only():
    root = XmlElement(
        "root",
        children=[
            XmlElement("p", {"id": "0"}),
            XmlElement("p", {"id": "1"}),
        ],
    )
    assert root.find("p").get("id") == "0"
    assert root.find("missing") is None


def test_findall_preserves_order():
    root = XmlElement(
        "root",
        children=[XmlElement("p", {"id": str(i)}) for i in range(5)],
    )
    assert [p.get("id") for p in root.findall("p")] == ["0", "1", "2", "3", "4"]


def test_get_returns_raw_strings_and_a_default():
    element = XmlElement("a", {"PixelSize": "1.3680"})
    assert element.get("PixelSize") == "1.3680"
    assert element.get("missing") is None
    assert element.get("missing", "fallback") == "fallback"


def test_iter_walks_the_whole_tree_in_document_order():
    root = XmlElement(
        "root",
        children=[
            XmlElement("a", children=[XmlElement("a1")]),
            XmlElement("b"),
        ],
    )
    assert [e.tag for e in root.iter()] == ["root", "a", "a1", "b"]


def test_sequence_protocol():
    child = XmlElement("child")
    root = XmlElement("root", children=[child])
    assert len(root) == 1
    assert root[0] is child
    assert list(root) == [child]


def test_declaration_serialisation():
    assert XmlDeclaration().to_string() == '<?xml version="1.0" encoding="utf-8"?>'
    assert XmlDeclaration(encoding=None).to_string() == '<?xml version="1.0"?>'
    assert XmlDeclaration(standalone="yes").to_string() == (
        '<?xml version="1.0" encoding="utf-8" standalone="yes"?>'
    )


def test_filename_is_excluded_from_equality(xml_path):
    """A document read from disk equals the same document parsed from text."""
    from_disk = xmlfile.read(xml_path)
    from_text = xmlfile.from_string(xml_path.read_text(encoding="utf-8"))
    assert from_disk.filename == xml_path
    assert from_text.filename is None
    assert from_disk == from_text


def test_document_coerces_filename_to_path():
    doc = XmlDocument(root=XmlElement("a"), filename="some/where.xml")
    assert isinstance(doc.filename, Path)
