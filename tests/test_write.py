"""Test category 3: write to disk and read back."""

from __future__ import annotations

import pytest

import xmlfile


def test_write_read_round_trip(xml_path, tmp_path):
    doc = xmlfile.read(xml_path)
    destination = tmp_path / "copy.xml"
    xmlfile.write(doc, destination)
    assert xmlfile.read(destination) == doc


def test_written_file_is_byte_identical(xml_path, tmp_path):
    doc = xmlfile.read(xml_path)
    destination = tmp_path / "copy.xml"
    xmlfile.write(doc, destination)
    assert destination.read_bytes() == xml_path.read_bytes()


def test_write_overwrites_by_default(xml_path, tmp_path):
    """Matches starfile and mdocfile, and supports editing a file in place."""
    doc = xmlfile.read(xml_path)
    destination = tmp_path / "copy.xml"
    xmlfile.write(doc, destination)
    xmlfile.write(doc, destination)
    assert xmlfile.read(destination) == doc


def test_write_can_be_told_to_refuse(xml_path, tmp_path):
    doc = xmlfile.read(xml_path)
    destination = tmp_path / "copy.xml"
    xmlfile.write(doc, destination)

    with pytest.raises(FileExistsError):
        xmlfile.write(doc, destination, overwrite=False)


def test_edited_document_can_be_written_back_over_itself(xml_path, tmp_path):
    """The perturb-and-rerun workflow: change a value, write it back."""
    working = tmp_path / "TS.xml"
    working.write_bytes(xml_path.read_bytes())

    doc = xmlfile.read(working)
    doc.root.attributes["Bfactor"] = "-42"
    xmlfile.write(doc, working)

    assert xmlfile.read(working).root.get("Bfactor") == "-42"


def test_write_without_declaration(xml_path, tmp_path):
    doc = xmlfile.read(xml_path)
    destination = tmp_path / "copy.xml"
    xmlfile.write(doc, destination, xml_declaration=False, byte_order_mark=False)
    text = destination.read_text(encoding="utf-8")
    assert not text.startswith("﻿")
    assert "<?xml" not in text
    assert xmlfile.read(destination).root == doc.root


def test_write_without_byte_order_mark(xml_path, tmp_path):
    doc = xmlfile.read(xml_path)
    destination = tmp_path / "copy.xml"
    xmlfile.write(doc, destination, byte_order_mark=False)
    assert not destination.read_bytes().startswith(b"\xef\xbb\xbf")
    assert xmlfile.read(destination).root == doc.root


def test_empty_elements_can_be_expanded(tmp_path):
    doc = xmlfile.from_string('<?xml version="1.0"?>\n<a><b /></a>')
    assert "<b />" in xmlfile.to_string(doc)
    assert "<b></b>" in xmlfile.to_string(doc, preserve_empty_elements=False)
