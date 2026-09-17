"""Test category 5: malformed input and safety failures."""

from __future__ import annotations

import pytest

import xmlfile
from xmlfile import XmlParseError


def test_missing_file_raises_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        xmlfile.read(tmp_path / "does_not_exist.xml")


def test_directory_raises(tmp_path):
    with pytest.raises(IsADirectoryError):
        xmlfile.read(tmp_path)


def test_malformed_xml_raises_a_useful_error(tmp_path):
    path = tmp_path / "broken.xml"
    path.write_text('<?xml version="1.0"?>\n<a><b></a>', encoding="utf-8")

    with pytest.raises(XmlParseError) as error:
        xmlfile.read(path)

    assert "broken.xml" in str(error.value)


def test_malformed_string_raises(tmp_path):
    with pytest.raises(XmlParseError):
        xmlfile.from_string("<a><b></a>")


def test_parse_error_is_a_value_error():
    """Callers may catch the broader type."""
    assert issubclass(XmlParseError, ValueError)


def test_write_needs_a_filename():
    from xmlfile.models import XmlDocument, XmlElement
    from xmlfile.writer import XmlWriter

    with pytest.raises(ValueError):
        XmlWriter(XmlDocument(root=XmlElement("a"))).write()


def test_parser_requires_exactly_one_source(tmp_path):
    from xmlfile.parser import XmlParser

    with pytest.raises(TypeError):
        XmlParser()
    with pytest.raises(TypeError):
        XmlParser(tmp_path / "a.xml", text="<a/>")
