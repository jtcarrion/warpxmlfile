"""Helpers for common patterns in XML metadata files.

The core model stores everything as strings. These functions are where values
are coerced to numbers, lists and arrays, and back. They are generic: a
"grid" is any element whose ``Node`` children carry integer ``X``/``Y``/``Z``
(and optionally ``W``) indices and a ``Value``; a "param" block is any element
whose ``Param`` children carry ``Name`` and ``Value``; a "pair series" is text
of the form ``x|y;x|y;...``. Nothing here knows what those quantities mean.

Number formatting on the way out is controlled by a ``value_format`` keyword.
Its default, ``"float32"``, writes the shortest text that round-trips the
value as a 32-bit float, in the style of .NET (no trailing ``.0``, upper-case
exponent). That is the format Warp writes, so a value that was read from a
Warp file and written back is reproduced byte for byte.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import numpy as np

from .models import XmlElement

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from .typing import ValueFormat

__all__ = [
    "array_to_grid",
    "grid_margins",
    "grid_to_array",
    "list_to_text",
    "pair_series_to_text",
    "params_to_dict",
    "params_to_pairs",
    "parse_pair_series",
    "text_to_list",
]

_AXES = ("X", "Y", "Z", "W")
_SIZE_ATTRIBUTES = ("Width", "Height", "Depth", "Duration")
_MARGIN_ATTRIBUTES = ("MarginX", "MarginY", "MarginZ", "MarginW")


# -- number formatting -------------------------------------------------------


def _format_float32(value: float) -> str:
    text = str(np.float32(value))
    if text.endswith(".0"):
        text = text[:-2]
    return text.replace("e", "E")


def _formatter(value_format: ValueFormat) -> Callable[[Any], str]:
    if value_format == "float32":
        return _format_float32
    if isinstance(value_format, str):
        if "%" in value_format:
            return lambda value: value_format % value
        return value_format.format
    return value_format


def _to_text(value: Any, format_number: Callable[[Any], str]) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, bool | np.bool_):
        return "True" if value else "False"
    if isinstance(value, int | np.integer):
        return str(int(value))
    return format_number(value)


# -- whitespace-separated lists ----------------------------------------------


def text_to_list(element: XmlElement, dtype: type = str) -> list[Any]:
    """Split an element's text on whitespace and coerce each item to `dtype`.

    Parameters
    ----------
    element
        Element whose text holds whitespace-separated values, one per line
        in Warp-style files.
    dtype
        ``str`` (default), ``int``, ``float`` or ``bool``. ``bool`` accepts
        ``True``/``False`` in any case and rejects everything else.
    """
    items = element.text.split() if element.text is not None else []
    if dtype is str:
        return items
    if dtype is bool:
        result: list[Any] = []
        for item in items:
            lowered = item.lower()
            if lowered not in ("true", "false"):
                raise ValueError(f"<{element.tag}>: {item!r} is not a boolean")
            result.append(lowered == "true")
        return result
    return [dtype(item) for item in items]


def list_to_text(
    values: Iterable[Any],
    *,
    separator: str = "\n",
    value_format: ValueFormat = "float32",
) -> str:
    """Join values into element text, the inverse of `text_to_list`.

    Parameters
    ----------
    values
        Strings are written as they are, booleans as ``True``/``False``,
        integers as integers and other numbers through `value_format`.
    separator
        Placed between values; a newline, as in Warp-style files.
    value_format
        ``"float32"`` (default; see the module docstring), a ``%`` or ``{}``
        format string, or a callable taking a number and returning text.
    """
    format_number = _formatter(value_format)
    return separator.join(_to_text(value, format_number) for value in values)


# -- <Param Name="..." Value="..."/> blocks ---------------------------------


def params_to_pairs(element: XmlElement) -> list[tuple[str, str]]:
    """Return the ``(Name, Value)`` of every ``Param`` child, in document order.

    Parameters
    ----------
    element
        Element whose ``Param`` children carry ``Name`` and ``Value``
        attributes. A ``Param`` missing either attribute raises ``ValueError``.
    """
    pairs = []
    for child in element.findall("Param"):
        name, value = child.get("Name"), child.get("Value")
        if name is None or value is None:
            raise ValueError(f"<{element.tag}>: Param without Name and Value")
        pairs.append((name, value))
    return pairs


def params_to_dict(
    element: XmlElement, *, allow_duplicates: bool = False
) -> dict[str, str]:
    """Return the ``Param`` children of `element` as a ``{Name: Value}`` dict.

    Parameters
    ----------
    element
        Element whose ``Param`` children carry ``Name`` and ``Value``.
    allow_duplicates
        A repeated ``Name`` raises ``ValueError`` unless this is True, in
        which case the last value wins.
    """
    result: dict[str, str] = {}
    for name, value in params_to_pairs(element):
        if name in result and not allow_duplicates:
            raise ValueError(f"<{element.tag}>: duplicate Param Name {name!r}")
        result[name] = value
    return result


# -- grids of <Node X= Y= Z= [W=] Value=/> -----------------------------------


def grid_to_array(element: XmlElement) -> np.ndarray:
    """Return the ``Node`` values of a grid element as a float32 array.

    The shape is ``(Depth, Height, Width)``, or ``(Duration, Depth, Height,
    Width)`` when the element has a ``Duration`` attribute, so that
    ``array[z, y, x]`` (or ``array[w, z, y, x]``) is the node with those
    indices and ``array.ravel()`` lists the nodes with ``X`` varying fastest.

    Parameters
    ----------
    element
        Element with ``Width``/``Height``/``Depth`` (and optionally
        ``Duration``) attributes and one ``Node`` child per grid point.
        Missing, duplicated or out-of-range nodes raise ``ValueError``.
    """
    ndim = 4 if "Duration" in element.attributes else 3
    sizes_xyz = tuple(
        int(element.attributes.get(name, "1")) for name in _SIZE_ATTRIBUTES[:ndim]
    )
    values = np.zeros(sizes_xyz[::-1], dtype=np.float32)
    seen = np.zeros(sizes_xyz[::-1], dtype=bool)
    nodes = element.findall("Node")
    if len(nodes) != values.size:
        raise ValueError(
            f"<{element.tag}>: {len(nodes)} Node children, expected {values.size}"
        )
    for node in nodes:
        index = tuple(int(node.attributes.get(axis, "0")) for axis in _AXES[:ndim])[
            ::-1
        ]
        if any(i < 0 or i >= n for i, n in zip(index, values.shape, strict=True)):
            raise ValueError(f"<{element.tag}>: Node {index[::-1]} is out of range")
        if seen[index]:
            raise ValueError(f"<{element.tag}>: Node {index[::-1]} appears twice")
        seen[index] = True
        values[index] = float(node.attributes.get("Value", "0"))
    return values


def grid_margins(element: XmlElement) -> tuple[float, ...]:
    """Return ``(MarginX, MarginY, MarginZ[, MarginW])`` of a grid element.

    Parameters
    ----------
    element
        A grid element. Margins not present in the file are omitted, so an
        element without margin attributes gives an empty tuple.
    """
    return tuple(
        float(element.attributes[name])
        for name in _MARGIN_ATTRIBUTES
        if name in element.attributes
    )


def array_to_grid(
    values: np.ndarray,
    tag: str,
    *,
    margins: Iterable[float] = (),
    template: XmlElement | None = None,
    value_format: ValueFormat = "float32",
) -> XmlElement:
    """Build a grid element, the inverse of `grid_to_array`.

    Parameters
    ----------
    values
        3-D ``(Depth, Height, Width)`` or 4-D ``(Duration, Depth, Height,
        Width)`` array. A 4-D array produces a ``Duration`` attribute.
    tag
        Tag of the element to create.
    margins
        Written as ``MarginX``, ``MarginY``, ... in that order; empty writes
        no margin attributes. Must have one entry per array dimension if given.
    template
        An existing grid element whose ``text``, ``tail`` and per-``Node``
        tails are copied, so that replacing it with the result keeps the
        document's indentation. Without a template, nodes are indented with
        tabs in the Warp style.
    value_format
        Formatting of each ``Value``; see `list_to_text`.
    """
    values = np.asarray(values)
    if values.ndim not in (3, 4):
        raise ValueError(f"values must be 3-D or 4-D, got shape {values.shape}")
    margins = tuple(margins)
    if margins and len(margins) != values.ndim:
        raise ValueError(f"{len(margins)} margins for a {values.ndim}-D grid")
    format_number = _formatter(value_format)

    sizes_xyz = values.shape[::-1]
    size_names = _SIZE_ATTRIBUTES[: values.ndim]
    attributes = {
        name: str(size) for name, size in zip(size_names, sizes_xyz, strict=True)
    }
    margin_names = _MARGIN_ATTRIBUTES[: len(margins)]
    for name, margin in zip(margin_names, margins, strict=True):
        attributes[name] = format_number(margin)

    if template is not None and template.children:
        text = template.text
        node_tail = template.children[0].tail
        last_tail = template.children[-1].tail
        tail = template.tail
    else:
        text, node_tail, last_tail = "\n\t\t", "\n\t\t", "\n\t"
        tail = template.tail if template is not None else None

    axes = _AXES[: values.ndim]
    nodes = []
    for index in np.ndindex(values.shape):
        node_attributes = {
            axis: str(i) for axis, i in zip(axes, index[::-1], strict=True)
        }
        node_attributes["Value"] = format_number(values[index])
        nodes.append(XmlElement("Node", node_attributes, tail=node_tail))
    if nodes:
        nodes[-1].tail = last_tail
    else:
        text = None
    return XmlElement(tag, attributes, text=text, children=nodes, tail=tail)


# -- pair series: "x|y;x|y;..." ------------------------------------------------


def parse_pair_series(element: XmlElement) -> np.ndarray:
    """Return the ``x|y;x|y;...`` text of `element` as an ``(n, 2)`` array.

    Parameters
    ----------
    element
        Element whose text is a ``;``-separated list of ``x|y`` pairs. A
        malformed pair raises ``ValueError``.
    """
    text = element.text.strip() if element.text is not None else ""
    if not text:
        return np.zeros((0, 2), dtype=np.float64)
    pairs = []
    for item in text.split(";"):
        parts = item.split("|")
        if len(parts) != 2:
            raise ValueError(f"<{element.tag}>: {item!r} is not an x|y pair")
        pairs.append((float(parts[0]), float(parts[1])))
    return np.asarray(pairs, dtype=np.float64)


def pair_series_to_text(
    values: np.ndarray, *, value_format: ValueFormat = "float32"
) -> str:
    """Join an ``(n, 2)`` array into ``x|y;x|y;...`` text.

    Parameters
    ----------
    values
        Array of shape ``(n, 2)``.
    value_format
        Formatting of each number; see `list_to_text`.
    """
    values = np.asarray(values)
    if values.ndim != 2 or values.shape[1] != 2:
        raise ValueError(f"values must have shape (n, 2), got {values.shape}")
    format_number = _formatter(value_format)
    return ";".join(f"{format_number(x)}|{format_number(y)}" for x, y in values)
