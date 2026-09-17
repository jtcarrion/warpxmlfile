"""Read and write XML metadata files in Python."""

from __future__ import annotations

from .functions import from_string, read, to_string, write
from .helpers import (
    array_to_grid,
    grid_margins,
    grid_to_array,
    list_to_text,
    pair_series_to_text,
    params_to_dict,
    params_to_pairs,
    parse_pair_series,
    text_to_list,
)
from .models import XmlDeclaration, XmlDocument, XmlElement
from .parser import XmlLossyContentWarning, XmlParseError

__all__ = [
    "XmlDeclaration",
    "XmlDocument",
    "XmlElement",
    "XmlLossyContentWarning",
    "XmlParseError",
    "array_to_grid",
    "from_string",
    "grid_margins",
    "grid_to_array",
    "list_to_text",
    "pair_series_to_text",
    "params_to_dict",
    "params_to_pairs",
    "parse_pair_series",
    "read",
    "text_to_list",
    "to_string",
    "write",
]

try:  # pragma: no cover - depends on install method
    from importlib.metadata import PackageNotFoundError, version

    __version__ = version("xmlfile")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.0.dev0"
