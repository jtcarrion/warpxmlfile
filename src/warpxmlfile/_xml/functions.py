"""The public functions of `xmlfile`: read, write, to_string, from_string.

This layer is deliberately thin. All of the work happens in `XmlParser` and
`XmlWriter`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .parser import XmlParser
from .writer import XmlWriter

if TYPE_CHECKING:
    from .models import XmlDocument
    from .typing import PathLike

__all__ = ["from_string", "read", "to_string", "write"]


def read(filename: PathLike, *, preserve_whitespace: bool = True) -> XmlDocument:
    """Read an XML file into an `XmlDocument`.

    Parameters
    ----------
    filename
        Path to the file.
    preserve_whitespace
        Keep the whitespace between elements (the default), so the document
        can be written back byte for byte. Set False for a purely semantic
        tree in which whitespace-only text and tails are dropped.
    """
    return XmlParser(filename, preserve_whitespace=preserve_whitespace).document


def from_string(text: str, *, preserve_whitespace: bool = True) -> XmlDocument:
    """Parse XML held in a string into an `XmlDocument`.

    Parameters
    ----------
    text
        The XML source.
    preserve_whitespace
        Keep the whitespace between elements (the default), so the document
        can be written back byte for byte. Set False for a purely semantic
        tree in which whitespace-only text and tails are dropped.
    """
    return XmlParser(text=text, preserve_whitespace=preserve_whitespace).document


def to_string(
    document: XmlDocument,
    *,
    xml_declaration: bool = True,
    byte_order_mark: bool | None = None,
    indent: str | None = None,
    preserve_empty_elements: bool = True,
) -> str:
    """Serialise an `XmlDocument` to a string.

    By default the stored whitespace is reproduced verbatim. Pass
    ``indent="  "`` to pretty-print instead, which reformats the document.

    Parameters
    ----------
    document
        The document to serialise.
    xml_declaration
        Whether to emit the ``<?xml ... ?>`` declaration.
    byte_order_mark
        Whether to emit a UTF-8 BOM. Defaults to whatever the document had.
    indent
        ``None`` (default) writes stored whitespace verbatim. A string
        switches on pretty-printing at that indentation.
    preserve_empty_elements
        When True, an element with no children and no text is written in the
        self-closing form ``<tag />``. When False it is written ``<tag></tag>``.
    """
    return XmlWriter(
        document,
        xml_declaration=xml_declaration,
        byte_order_mark=byte_order_mark,
        indent=indent,
        preserve_empty_elements=preserve_empty_elements,
    ).to_string()


def write(
    document: XmlDocument,
    filename: PathLike,
    *,
    encoding: str | None = None,
    xml_declaration: bool = True,
    byte_order_mark: bool | None = None,
    indent: str | None = None,
    preserve_empty_elements: bool = True,
    overwrite: bool = True,
) -> None:
    """Write an `XmlDocument` to a file.

    Replaces an existing file, like `starfile` and `mdocfile` do. Pass
    ``overwrite=False`` to refuse instead.

    Parameters
    ----------
    document
        The document to write.
    filename
        Destination path.
    encoding
        Encoding of the written bytes. Defaults to the document's declared
        encoding, or utf-8.
    xml_declaration
        Whether to emit the ``<?xml ... ?>`` declaration.
    byte_order_mark
        Whether to emit a UTF-8 BOM. Defaults to whatever the document had.
    indent
        ``None`` (default) writes stored whitespace verbatim. A string
        switches on pretty-printing at that indentation.
    preserve_empty_elements
        When True, an element with no children and no text is written in the
        self-closing form ``<tag />``. When False it is written ``<tag></tag>``.
    overwrite
        Whether an existing file may be replaced. True by default.
    """
    XmlWriter(
        document,
        filename=filename,
        encoding=encoding,
        xml_declaration=xml_declaration,
        byte_order_mark=byte_order_mark,
        indent=indent,
        preserve_empty_elements=preserve_empty_elements,
        overwrite=overwrite,
    ).write()
