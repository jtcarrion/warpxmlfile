"""The public functions of `xmlfile`: read, write, to_string, from_string.

This layer is deliberately thin. All of the work happens in `XmlParser` and
`XmlWriter`.
"""

from __future__ import annotations

from .models import XmlDocument
from .parser import XmlParser
from .typing import PathLike
from .writer import XmlWriter

__all__ = ["read", "from_string", "to_string", "write"]


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
    """Parse XML held in a string into an `XmlDocument`."""
    return XmlParser(text=text, preserve_whitespace=preserve_whitespace).document


def to_string(document: XmlDocument, **kwargs) -> str:
    """Serialise an `XmlDocument` to a string.

    By default the stored whitespace is reproduced verbatim. Pass
    ``indent="  "`` to pretty-print instead, which reformats the document.
    See `XmlWriter` for the full set of options.
    """
    return XmlWriter(document, **kwargs).to_string()


def write(document: XmlDocument, filename: PathLike, **kwargs) -> None:
    """Write an `XmlDocument` to a file.

    Replaces an existing file, like `starfile` and `mdocfile` do. Pass
    ``overwrite=False`` to refuse instead. See `XmlWriter` for all options.
    """
    XmlWriter(document, filename=filename, **kwargs).write()
