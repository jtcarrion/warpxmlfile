"""Generic ordered XML engine (private).

Byte-exact read/write of arbitrary XML into passive containers. `warpxmlfile`
builds its Warp tilt-series model on top of this; the engine itself knows
nothing about Warp.
"""

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
