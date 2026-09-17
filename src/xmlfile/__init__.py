"""Read and write XML metadata files in Python."""

from __future__ import annotations

from .functions import from_string, read, to_string, write
from .models import XmlDeclaration, XmlDocument, XmlElement
from .parser import XmlLossyContentWarning, XmlParseError

__all__ = [
    "XmlDeclaration",
    "XmlDocument",
    "XmlElement",
    "XmlLossyContentWarning",
    "XmlParseError",
    "from_string",
    "read",
    "to_string",
    "write",
]

try:  # pragma: no cover - depends on install method
    from importlib.metadata import PackageNotFoundError, version

    __version__ = version("xmlfile")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.0.dev0"
