"""Parsing of XML files and strings into `XmlDocument` objects.

Uses `xml.parsers.expat` from the standard library rather than
`xml.etree.ElementTree`. ElementTree performs namespace processing, which
rewrites ``<w:b>`` to ``{uri}b`` and discards the ``xmlns:w`` declaration
outright. Discarding an attribute is exactly what this package exists to
avoid, so expat is driven directly with namespace processing switched off:
prefixes stay part of the tag name and ``xmlns`` declarations remain ordinary
attributes.

Nothing is dropped, reordered, or coerced. Unknown elements and attributes are
preserved because the model is generic and has no notion of "known".

Known limitation: comments and processing instructions inside the document are
not represented in the model and are lost on a round trip. This is the only
case in which content is dropped, and it is never silent: an
`XmlLossyContentWarning` is issued. See the README.
"""

from __future__ import annotations

import re
import warnings
from pathlib import Path
from xml.parsers import expat

from .models import XmlDeclaration, XmlDocument, XmlElement
from .typing import PathLike
from .utils import is_insignificant_whitespace

__all__ = ["XmlParser", "XmlParseError", "XmlLossyContentWarning"]

_BOM = "﻿"

_DECLARATION_RE = re.compile(
    r"""^<\?xml
        \s+version\s*=\s*(?P<q>["'])(?P<version>[^"']*)(?P=q)
        (?:\s+encoding\s*=\s*["'](?P<encoding>[^"']*)["'])?
        (?:\s+standalone\s*=\s*["'](?P<standalone>[^"']*)["'])?
        \s*\?>""",
    re.VERBOSE,
)


class XmlParseError(ValueError):
    """Raised when a document cannot be parsed as XML."""


class XmlLossyContentWarning(UserWarning):
    """Warns that content was read but cannot be represented in the model.

    Comments and processing instructions are the only such content. They are
    discarded, so a document containing them will not round trip exactly.
    """


class _TreeBuilder:
    """Assembles `XmlElement` objects from expat callbacks."""

    def __init__(self) -> None:
        self.root: XmlElement | None = None
        self.dropped: list[str] = []
        self._stack: list[XmlElement] = []
        self._data: list[str] = []

    def _flush(self) -> None:
        if not self._data:
            return
        text = "".join(self._data)
        self._data.clear()
        if not self._stack:
            # Character data outside the root element. Whitespace there is
            # recorded on the document as `prologue_tail`/`epilogue`.
            return
        current = self._stack[-1]
        if current.children:
            last = current.children[-1]
            last.tail = (last.tail or "") + text
        else:
            current.text = (current.text or "") + text

    def start(self, tag: str, attributes: list[str]) -> None:
        self._flush()
        # `ordered_attributes` gives a flat [name, value, name, value, ...]
        # list, which is how attribute order is preserved.
        pairs = {
            attributes[i]: attributes[i + 1] for i in range(0, len(attributes), 2)
        }
        element = XmlElement(tag=tag, attributes=pairs)
        if self._stack:
            self._stack[-1].children.append(element)
        elif self.root is None:
            self.root = element
        self._stack.append(element)

    def end(self, tag: str) -> None:
        self._flush()
        self._stack.pop()

    def data(self, text: str) -> None:
        self._data.append(text)

    def comment(self, text: str) -> None:
        self._flush()
        self.dropped.append("comment")

    def processing_instruction(self, target: str, data: str) -> None:
        self._flush()
        self.dropped.append("processing instruction")


class XmlParser:
    """Parse XML text or a file into an `XmlDocument`.

    Parameters
    ----------
    source
        A path to read, when `text` is not given.
    text
        XML source to parse directly, as a string.
    preserve_whitespace
        When True (the default) element text and tail are kept exactly as
        they appear, including the whitespace a pretty-printer inserted. When
        False, whitespace-only text and tail are discarded, leaving a purely
        semantic tree.
    """

    def __init__(
        self,
        source: PathLike | None = None,
        *,
        text: str | None = None,
        preserve_whitespace: bool = True,
    ) -> None:
        if (source is None) == (text is None):
            raise TypeError("provide exactly one of `source` or `text`")

        self.preserve_whitespace = preserve_whitespace
        self.filename: Path | None = None

        if source is not None:
            self.filename = Path(source)
            text = self._read_text(self.filename)

        assert text is not None
        self.document = self._parse(text)

    # -- reading ------------------------------------------------------------

    @staticmethod
    def _read_text(path: Path) -> str:
        if path.is_dir():
            raise IsADirectoryError(f"expected a file, got a directory: {path}")
        if not path.exists():
            raise FileNotFoundError(f"no such file: {path}")
        # `utf-8-sig` would silently strip the BOM; decode as plain utf-8 so
        # that its presence is recorded and can be written back.
        data = path.read_bytes()
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError as error:
            raise XmlParseError(f"{path} is not valid UTF-8: {error}") from error

    # -- parsing ------------------------------------------------------------

    def _parse(self, text: str) -> XmlDocument:
        byte_order_mark = text.startswith(_BOM)
        if byte_order_mark:
            text = text[len(_BOM) :]

        declaration, body = self._split_declaration(text)

        # Whitespace around the root is not reported by expat's character data
        # handler, so measure it against the source text directly.
        prologue_tail = body[: len(body) - len(body.lstrip())]
        epilogue = body[len(body.rstrip()) :]

        root = self._build(body)

        return XmlDocument(
            root=root,
            declaration=declaration,
            byte_order_mark=byte_order_mark,
            prologue_tail=prologue_tail if self.preserve_whitespace else "",
            epilogue=epilogue if self.preserve_whitespace else "",
            filename=self.filename,
        )

    @staticmethod
    def _split_declaration(text: str) -> tuple[XmlDeclaration | None, str]:
        match = _DECLARATION_RE.match(text)
        if match is None:
            return None, text
        declaration = XmlDeclaration(
            version=match.group("version"),
            encoding=match.group("encoding"),
            standalone=match.group("standalone"),
            quote=match.group("q"),
        )
        return declaration, text[match.end() :]

    def _build(self, body: str) -> XmlElement:
        builder = _TreeBuilder()

        # No `namespace_separator`, so expat leaves prefixed names and xmlns
        # declarations exactly as written.
        parser = expat.ParserCreate()
        parser.ordered_attributes = True
        parser.buffer_text = True
        parser.StartElementHandler = builder.start
        parser.EndElementHandler = builder.end
        parser.CharacterDataHandler = builder.data
        parser.CommentHandler = builder.comment
        parser.ProcessingInstructionHandler = builder.processing_instruction
        parser.ExternalEntityRefHandler = self._refuse_external_entity

        try:
            parser.Parse(body.encode("utf-8"), True)
        except expat.ExpatError as error:
            where = self.filename if self.filename is not None else "<string>"
            raise XmlParseError(f"could not parse {where}: {error}") from error

        if builder.root is None:  # pragma: no cover - expat rejects this first
            where = self.filename if self.filename is not None else "<string>"
            raise XmlParseError(f"{where} contains no root element")

        if builder.dropped:
            where = self.filename if self.filename is not None else "<string>"
            counts = {kind: builder.dropped.count(kind) for kind in set(builder.dropped)}
            detail = ", ".join(f"{n} {kind}(s)" for kind, n in sorted(counts.items()))
            warnings.warn(
                f"{where}: {detail} discarded; this document will not round "
                f"trip exactly",
                XmlLossyContentWarning,
                stacklevel=4,
            )

        root = builder.root
        root.tail = None  # text after the root is held as `epilogue`

        if not self.preserve_whitespace:
            self._strip_whitespace(root)

        return root

    @staticmethod
    def _refuse_external_entity(*args: object) -> bool:
        """Never resolve external entities; they can read arbitrary files."""
        raise XmlParseError("external entity references are not supported")

    def _strip_whitespace(self, element: XmlElement) -> None:
        if is_insignificant_whitespace(element.text):
            element.text = None
        if is_insignificant_whitespace(element.tail):
            element.tail = None
        for child in element.children:
            self._strip_whitespace(child)
