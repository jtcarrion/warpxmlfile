"""Passive, ordered containers for XML documents.

These objects hold what was in the file and nothing more. They perform no
numeric conversion, no reordering, and no scientific interpretation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

__all__ = ["XmlDeclaration", "XmlDocument", "XmlElement"]


@dataclass
class XmlDeclaration:
    """The ``<?xml ... ?>`` declaration at the top of a document."""

    version: str = "1.0"
    encoding: str | None = "utf-8"
    standalone: str | None = None
    quote: str = '"'

    def to_string(self) -> str:
        """Return the declaration as it is written at the top of a file."""
        q = self.quote
        parts = [f"version={q}{self.version}{q}"]
        if self.encoding is not None:
            parts.append(f"encoding={q}{self.encoding}{q}")
        if self.standalone is not None:
            parts.append(f"standalone={q}{self.standalone}{q}")
        return "<?xml " + " ".join(parts) + "?>"


@dataclass
class XmlElement:
    """A single XML element.

    Attributes
    ----------
    tag
        The element name, exactly as it appeared in the file.
    attributes
        Attribute names to raw string values, in document order.
    text
        Character data between the start tag and the first child, verbatim.
        ``None`` means the element had no character data at all.
    children
        Child elements in document order. Repeated tags are preserved
        naturally because this is a list, not a mapping.
    tail
        Character data between this element's end tag and the next sibling,
        verbatim. Needed for faithful round-tripping of indentation.
    """

    tag: str
    attributes: dict[str, str] = field(default_factory=dict)
    text: str | None = None
    children: list[XmlElement] = field(default_factory=list)
    tail: str | None = None

    # -- navigation helpers -------------------------------------------------
    # These locate elements. They do not interpret them.

    def find(self, tag: str) -> XmlElement | None:
        """Return the first direct child with `tag`, or None.

        Parameters
        ----------
        tag
            Element name to look for, compared exactly.
        """
        for child in self.children:
            if child.tag == tag:
                return child
        return None

    def findall(self, tag: str) -> list[XmlElement]:
        """Return all direct children with `tag`, in document order.

        Parameters
        ----------
        tag
            Element name to look for, compared exactly.
        """
        return [child for child in self.children if child.tag == tag]

    def get(self, name: str, default: str | None = None) -> str | None:
        """Return the raw string value of attribute `name`.

        Parameters
        ----------
        name
            Attribute name.
        default
            Returned when the attribute is absent.
        """
        return self.attributes.get(name, default)

    def iter(self) -> Iterator[XmlElement]:
        """Yield this element and every descendant, in document order."""
        yield self
        for child in self.children:
            yield from child.iter()

    def __len__(self) -> int:
        """Number of direct children."""
        return len(self.children)

    def __iter__(self) -> Iterator[XmlElement]:
        """Iterate over the direct children, in document order."""
        return iter(self.children)

    def __getitem__(self, index: int) -> XmlElement:
        """Return the direct child at `index`."""
        return self.children[index]


@dataclass
class XmlDocument:
    """A whole XML document: its root element plus everything around it.

    The fields beyond `root` exist so that a document can be written back out
    exactly as it was read, including the byte order mark and the whitespace
    between the declaration and the root element.
    """

    root: XmlElement
    declaration: XmlDeclaration | None = None
    byte_order_mark: bool = False
    prologue_tail: str = ""
    epilogue: str = ""
    # `filename` records provenance only. It is excluded from equality so that
    # a document read from disk compares equal to the same document parsed
    # from a string.
    filename: Path | None = field(default=None, compare=False)

    def __post_init__(self) -> None:
        """Normalise `filename` to a `Path`."""
        if self.filename is not None:
            self.filename = Path(self.filename)
