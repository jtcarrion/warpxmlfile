"""Serialisation of `XmlDocument` objects back to XML.

Two modes are available:

* faithful (``indent=None``, the default) - the whitespace stored in each
  element's ``text``/``tail`` is written back verbatim. Reading a file and
  writing it again reproduces it byte for byte.
* pretty (``indent="  "`` or similar) - insignificant whitespace is
  regenerated at the requested indentation. This *reformats* the document, so
  it is never the default.

Neither mode reorders children or attributes, and neither reformats numeric
text: values are written back exactly as they were stored.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from .utils import escape_attribute, escape_text, is_insignificant_whitespace

if TYPE_CHECKING:
    from .models import XmlDocument, XmlElement
    from .typing import PathLike

__all__ = ["XmlWriter"]

_BOM = "﻿"


class XmlWriter:
    """Serialise an `XmlDocument`.

    Parameters
    ----------
    document
        The document to serialise.
    filename
        Destination for `write`. Not needed for `to_string`.
    encoding
        Encoding used by `write`. Defaults to the document's declared
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
        Whether `write` may replace an existing file. True by default, matching
        `starfile` and `mdocfile`. Pass False to refuse instead.
    """

    def __init__(
        self,
        document: XmlDocument,
        *,
        filename: PathLike | None = None,
        encoding: str | None = None,
        xml_declaration: bool = True,
        byte_order_mark: bool | None = None,
        indent: str | None = None,
        preserve_empty_elements: bool = True,
        overwrite: bool = True,
    ) -> None:
        self.document = document
        self.filename = Path(filename) if filename is not None else None
        self.encoding = encoding
        self.xml_declaration = xml_declaration
        self.byte_order_mark = byte_order_mark
        self.indent = indent
        self.preserve_empty_elements = preserve_empty_elements
        self.overwrite = overwrite

    # -- public API ---------------------------------------------------------

    def to_string(self) -> str:
        """Return the serialised document as a string."""
        parts: list[str] = []

        use_bom = (
            self.document.byte_order_mark
            if self.byte_order_mark is None
            else self.byte_order_mark
        )
        if use_bom:
            parts.append(_BOM)

        declaration = self.document.declaration
        if self.xml_declaration and declaration is not None:
            parts.append(declaration.to_string())
            parts.append(self.document.prologue_tail if self.indent is None else "\n")
        elif declaration is None and self.indent is None:
            # No declaration to separate from the root, but any leading
            # whitespace the file had is still part of it.
            parts.append(self.document.prologue_tail)

        self._serialise(self.document.root, parts, level=0)
        parts.append(self.document.epilogue if self.indent is None else "")

        return "".join(parts)

    def write(self) -> None:
        """Write the serialised document to `filename`."""
        if self.filename is None:
            raise ValueError("no filename given; cannot write")
        if self.filename.exists() and not self.overwrite:
            raise FileExistsError(f"{self.filename} already exists and overwrite=False")

        encoding = self._resolve_encoding()
        text = self.to_string()
        self.filename.write_bytes(text.encode(encoding))

    # -- internals ----------------------------------------------------------

    def _resolve_encoding(self) -> str:
        if self.encoding is not None:
            return self.encoding
        declaration = self.document.declaration
        if declaration is not None and declaration.encoding is not None:
            return declaration.encoding
        return "utf-8"

    def _start_tag(self, element: XmlElement) -> str:
        attributes = "".join(
            f' {name}="{escape_attribute(value)}"'
            for name, value in element.attributes.items()
        )
        return f"<{element.tag}{attributes}"

    def _is_empty(self, element: XmlElement) -> bool:
        return not element.children and element.text is None

    def _serialise(self, element: XmlElement, parts: list[str], level: int) -> None:
        if self.indent is None:
            self._serialise_verbatim(element, parts)
        else:
            self._serialise_pretty(element, parts, level)

    def _serialise_verbatim(self, element: XmlElement, parts: list[str]) -> None:
        parts.append(self._start_tag(element))

        if self._is_empty(element) and self.preserve_empty_elements:
            parts.append(" />")
        else:
            parts.append(">")
            if element.text is not None:
                parts.append(escape_text(element.text))
            for child in element.children:
                self._serialise_verbatim(child, parts)
            parts.append(f"</{element.tag}>")

        if element.tail is not None:
            parts.append(escape_text(element.tail))

    def _serialise_pretty(
        self, element: XmlElement, parts: list[str], level: int
    ) -> None:
        indent = self.indent
        assert indent is not None  # only reached in pretty mode
        parts.append(self._start_tag(element))

        has_significant_text = not is_insignificant_whitespace(element.text)

        if self._is_empty(element) and self.preserve_empty_elements:
            parts.append(" />")
            return

        parts.append(">")

        if has_significant_text:
            # Mixed or text content: write it exactly as stored and keep any
            # children inline rather than risk changing what the text means.
            assert element.text is not None
            parts.append(escape_text(element.text))
            for child in element.children:
                self._serialise_pretty(child, parts, level + 1)
        elif element.children:
            for child in element.children:
                parts.append("\n" + indent * (level + 1))
                self._serialise_pretty(child, parts, level + 1)
            parts.append("\n" + indent * level)

        parts.append(f"</{element.tag}>")
