"""The Warp tilt-series model: what a Warp / M tilt-series XML says, as Python data.

Strings become numbers, booleans and arrays. Nothing is reinterpreted: no
units, no signs, no frames, no pixel conversion, no spline evaluation. The
parsed document is kept privately so that writing changes only what was
edited and leaves every other byte of the file alone.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import numpy as np
from pydantic import BaseModel, ConfigDict, PrivateAttr

from . import _convert, _xml
from ._xml import XmlDocument, XmlElement

if TYPE_CHECKING:
    from ._xml.typing import PathLike

__all__ = ["Grid", "WarpTiltSeries"]

# Per-tilt elements (newline-separated, one value per tilt) and their dtypes.
PER_TILT_FLOAT = {
    "angles": "Angles",
    "dose": "Dose",
    "axis_angle": "AxisAngle",
    "axis_offset_x": "AxisOffsetX",
    "axis_offset_y": "AxisOffsetY",
    "fov_fraction": "FOVFraction",
}
REQUIRED = ("Angles", "UseTilt", "AxisAngle", "AxisOffsetX", "AxisOffsetY")
PAIR_SERIES = {"tilt_ps1d": "TiltPS1D", "tilt_simulated_scale": "TiltSimulatedScale"}
KNOWN_TAGS = frozenset(
    {
        *PER_TILT_FLOAT.values(),
        "UseTilt",
        "MoviePath",
        "CTF",
        "OptionsCTF",
        *PAIR_SERIES.values(),
    }
)


class Grid(BaseModel):
    """A grid of ``Node`` values, e.g. ``GridMovementX`` or ``GridVolumeWarpX``.

    Attributes
    ----------
    values
        float32 array shaped ``(Depth, Height, Width)``, or ``(Duration, Depth,
        Height, Width)`` for a 4-D grid; ``values.ravel()`` lists the nodes with
        ``X`` varying fastest, as in the file.
    margins
        ``(MarginX, MarginY, MarginZ[, MarginW])`` as written; empty if absent.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    values: np.ndarray
    margins: tuple[float, ...] = ()


class WarpTiltSeries(BaseModel):
    """Deserialised content of a Warp / M tilt-series XML.

    Attributes
    ----------
    attributes
        Every root attribute, verbatim.
    angles, axis_angle, axis_offset_x, axis_offset_y
        Per-tilt float arrays of length ``n_tilts``. Offsets are in Angstroms,
        as in the file.
    dose, fov_fraction
        Float arrays as found in the file (``None`` when absent). Usually one
        value per tilt, but Warp may write a single value for the series, so
        their length is not enforced.
    use_tilt
        Per-tilt boolean array.
    movie_path
        Movie paths as found in the file, verbatim (usually one per tilt).
    ctf, options_ctf
        ``{Name: Value}`` of the ``Param`` children, values as text (``None``
        when the block is absent).
    grids
        Every ``Grid*`` element, by tag.
    tilt_ps1d, tilt_simulated_scale
        One ``(n, 2)`` array per repeated element.
    extra
        Tags of root children not represented above; they are preserved on
        write.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, validate_assignment=False)

    attributes: dict[str, str] = {}
    angles: np.ndarray
    use_tilt: np.ndarray
    axis_angle: np.ndarray
    axis_offset_x: np.ndarray
    axis_offset_y: np.ndarray
    dose: np.ndarray | None = None
    fov_fraction: np.ndarray | None = None
    movie_path: list[str] = []
    ctf: dict[str, str] | None = None
    options_ctf: dict[str, str] | None = None
    grids: dict[str, Grid] = {}
    tilt_ps1d: list[np.ndarray] = []
    tilt_simulated_scale: list[np.ndarray] = []
    extra: list[str] = []

    _document: XmlDocument | None = PrivateAttr(default=None)
    _parsed: dict[str, Any] = PrivateAttr(default_factory=dict)

    # -- derived views ----------------------------------------------------------

    @property
    def n_tilts(self) -> int:
        """Number of tilts, from ``Angles``."""
        return len(self.angles)

    @property
    def image_dimensions_angstrom(self) -> tuple[float, ...] | None:
        """``ImageDimensionsAngstrom`` root attribute as floats, or ``None``."""
        return _floats(self.attributes.get("ImageDimensionsAngstrom"))

    @property
    def volume_dimensions_angstrom(self) -> tuple[float, ...] | None:
        """``VolumeDimensionsAngstrom`` root attribute as floats, or ``None``."""
        return _floats(self.attributes.get("VolumeDimensionsAngstrom"))

    # -- construction ------------------------------------------------------------

    @classmethod
    def from_file(cls, filename: PathLike) -> WarpTiltSeries:
        """Read a Warp / M tilt-series XML file (same as `warpxmlfile.read`).

        Parameters
        ----------
        filename
            Path to the file.
        """
        return cls.from_document(_xml.read(filename))

    @classmethod
    def from_string(cls, text: str) -> WarpTiltSeries:
        """Parse XML text (same as `warpxmlfile.from_string`).

        Parameters
        ----------
        text
            The XML source.
        """
        return cls.from_document(_xml.from_string(text))

    def to_string(self) -> str:
        """Serialise to XML text (same as `warpxmlfile.to_string`)."""
        return _xml.to_string(self.to_document())

    def to_file(self, filename: PathLike, *, overwrite: bool = True) -> None:
        """Write to a file (same as `warpxmlfile.write`).

        Parameters
        ----------
        filename
            Destination path.
        overwrite
            Whether an existing file may be replaced.
        """
        _xml.write(self.to_document(), filename, overwrite=overwrite)

    @classmethod
    def from_document(cls, document: XmlDocument) -> WarpTiltSeries:
        """Deserialise a parsed document; the document is kept for `write`."""
        root = document.root
        for tag in REQUIRED:
            if root.find(tag) is None:
                raise ValueError(f"not a Warp tilt-series XML: no <{tag}> element")
        fields: dict[str, Any] = {"attributes": dict(root.attributes)}
        for name, tag in PER_TILT_FLOAT.items():
            element = root.find(tag)
            fields[name] = (
                None
                if element is None
                else np.asarray(_convert.text_to_list(element, float))
            )
        fields["use_tilt"] = np.asarray(
            _convert.text_to_list(_child(root, "UseTilt"), bool)
        )
        element = root.find("MoviePath")
        fields["movie_path"] = [] if element is None else _convert.text_to_list(element)
        for name, tag in (("ctf", "CTF"), ("options_ctf", "OptionsCTF")):
            element = root.find(tag)
            fields[name] = None if element is None else _convert.params_to_dict(element)
        fields["grids"] = {
            child.tag: Grid(
                values=_convert.grid_to_array(child),
                margins=_convert.grid_margins(child),
            )
            for child in root.children
            if child.tag.startswith("Grid")
        }
        for name, tag in PAIR_SERIES.items():
            fields[name] = [_convert.parse_pair_series(e) for e in root.findall(tag)]
        fields["extra"] = sorted(
            {
                c.tag
                for c in root.children
                if c.tag not in KNOWN_TAGS and not c.tag.startswith("Grid")
            }
        )

        # Required per-tilt elements must agree with <Angles>. Optional ones
        # (Dose, FOVFraction, MoviePath) are returned as found: Warp itself
        # writes e.g. a single FOVFraction value for a whole series.
        n = len(fields["angles"])
        for name, tag in PER_TILT_FLOAT.items():
            if tag in REQUIRED and len(fields[name]) != n:
                raise ValueError(
                    f"<{tag}> has {len(fields[name])} values, expected {n}"
                )
        if len(fields["use_tilt"]) != n:
            raise ValueError(
                f"<UseTilt> has {len(fields['use_tilt'])} values, expected {n}"
            )

        model = cls(**fields)
        model._document = document
        model._parsed = model._snapshot()
        return model

    # -- serialisation ----------------------------------------------------------

    def _snapshot(self) -> dict[str, Any]:
        """Deep-ish copy of the serialisable fields, for change detection."""
        return {
            "attributes": dict(self.attributes),
            **{
                name: None
                if getattr(self, name) is None
                else np.array(getattr(self, name))
                for name in PER_TILT_FLOAT
            },
            "use_tilt": np.array(self.use_tilt),
            "movie_path": list(self.movie_path),
            "ctf": None if self.ctf is None else dict(self.ctf),
            "options_ctf": None if self.options_ctf is None else dict(self.options_ctf),
            "grids": {
                k: (np.array(g.values), tuple(g.margins)) for k, g in self.grids.items()
            },
            **{
                name: [np.array(a) for a in getattr(self, name)] for name in PAIR_SERIES
            },
        }

    def to_document(self) -> XmlDocument:
        """Serialise, patching the parsed document; build a Warp-style one if none."""
        if self._document is None:
            return self._new_document()
        document = self._document
        root = document.root
        old = self._parsed
        if self.attributes != old["attributes"]:
            root.attributes = dict(self.attributes)
        for name, tag in PER_TILT_FLOAT.items():
            new = getattr(self, name)
            if not _same_array(new, old[name]):
                _set_text(
                    root, tag, None if new is None else _convert.list_to_text(new)
                )
        if not _same_array(self.use_tilt, old["use_tilt"]):
            _set_text(root, "UseTilt", _convert.list_to_text(self.use_tilt))
        if self.movie_path != old["movie_path"]:
            _set_text(
                root,
                "MoviePath",
                _convert.list_to_text(self.movie_path) if self.movie_path else None,
            )
        for name, tag in (("ctf", "CTF"), ("options_ctf", "OptionsCTF")):
            if getattr(self, name) != old[name]:
                _set_params(root, tag, getattr(self, name))
        for tag, grid in self.grids.items():
            previous = old["grids"].get(tag)
            if (
                previous is None
                or not _same_array(grid.values, previous[0])
                or tuple(grid.margins) != previous[1]
            ):
                _set_grid(root, tag, grid)
        for tag in set(old["grids"]) - set(self.grids):
            _remove(root, tag)
        for name, tag in PAIR_SERIES.items():
            new, before = getattr(self, name), old[name]
            elements = root.findall(tag)
            if len(new) != len(elements):
                raise ValueError(
                    f"changing the number of <{tag}> elements is not supported"
                )
            for element, array, prior in zip(elements, new, before, strict=True):
                if not _same_array(array, prior):
                    element.text = _convert.pair_series_to_text(array)
        return document

    def _new_document(self) -> XmlDocument:
        """A document in Warp's own layout (BOM, tabs, Warp's element order)."""
        root = XmlElement("TiltSeries", dict(self.attributes), text="\n\t")
        children: list[XmlElement] = []

        def add(
            tag: str, text: str | None = None, nodes: list[XmlElement] | None = None
        ) -> XmlElement:
            element = XmlElement(tag, text=text, children=nodes or [], tail="\n\t")
            children.append(element)
            return element

        per_tilt = [
            ("Angles", self.angles),
            ("Dose", self.dose),
            ("UseTilt", self.use_tilt),
            ("AxisAngle", self.axis_angle),
            ("AxisOffsetX", self.axis_offset_x),
            ("AxisOffsetY", self.axis_offset_y),
            ("MoviePath", self.movie_path or None),
            ("FOVFraction", self.fov_fraction),
        ]
        for tag, values in per_tilt:
            if values is not None:
                add(tag, _convert.list_to_text(values))
        for tag, params in (("CTF", self.ctf), ("OptionsCTF", self.options_ctf)):
            if params is not None:
                add(tag, text="\n\t\t", nodes=_param_children(params))
        for tag, grid in self.grids.items():
            element = _convert.array_to_grid(grid.values, tag, margins=grid.margins)
            element.tail = "\n\t"
            children.append(element)
        for name, tag in PAIR_SERIES.items():
            for i, array in enumerate(getattr(self, name)):
                add(tag, _convert.pair_series_to_text(array)).attributes["ID"] = str(i)
        if children:
            children[-1].tail = "\n"
        else:
            root.text = None
        root.children = children
        return XmlDocument(
            root=root,
            declaration=_declaration(),
            byte_order_mark=True,
            prologue_tail="\n",
        )


# -- helpers ---------------------------------------------------------------------


def _floats(text: str | None) -> tuple[float, ...] | None:
    return None if text is None else tuple(float(v) for v in text.split(","))


def _child(root: XmlElement, tag: str) -> XmlElement:
    element = root.find(tag)
    if element is None:
        raise ValueError(f"no <{tag}> element")
    return element


def _same_array(a: Any, b: Any) -> bool:
    if a is None or b is None:
        return a is None and b is None
    a, b = np.asarray(a), np.asarray(b)
    return a.shape == b.shape and bool(np.array_equal(a, b))


def _set_text(root: XmlElement, tag: str, text: str | None) -> None:
    element = root.find(tag)
    if text is None:
        if element is not None:
            _remove(root, tag)
        return
    if element is None:
        element = XmlElement(tag, tail="\n\t")
        _insert_after_last(root, element)
    element.text = text


def _remove(root: XmlElement, tag: str) -> None:
    element = root.find(tag)
    if element is None:
        return
    index = root.children.index(element)
    if index == len(root.children) - 1 and index > 0:
        root.children[index - 1].tail = element.tail  # keep the closing whitespace
    del root.children[index]


def _insert_after_last(root: XmlElement, element: XmlElement) -> None:
    if root.children:
        last = root.children[-1]
        element.tail, last.tail = last.tail, "\n\t"
    root.children.append(element)


def _param_children(
    params: dict[str, str], tail: str = "\n\t\t", last_tail: str = "\n\t"
) -> list[XmlElement]:
    nodes = [
        XmlElement("Param", {"Name": k, "Value": v}, tail=tail)
        for k, v in params.items()
    ]
    if nodes:
        nodes[-1].tail = last_tail
    return nodes


def _set_params(root: XmlElement, tag: str, params: dict[str, str] | None) -> None:
    element = root.find(tag)
    if params is None:
        _remove(root, tag)
        return
    if element is None:
        element = XmlElement(tag, text="\n\t\t", tail="\n\t")
        _insert_after_last(root, element)
        element.children = _param_children(params)
        return
    old_nodes = element.findall("Param")
    tail = old_nodes[0].tail if old_nodes else "\n\t\t"
    last_tail = old_nodes[-1].tail if old_nodes else "\n\t"
    element.children = _param_children(params, tail or "", last_tail or "")


def _set_grid(root: XmlElement, tag: str, grid: Grid) -> None:
    old = root.find(tag)
    new = _convert.array_to_grid(grid.values, tag, margins=grid.margins, template=old)
    if old is None:
        _insert_after_last(root, new)
    else:
        root.children[root.children.index(old)] = new


def _declaration() -> Any:
    from ._xml import XmlDeclaration

    return XmlDeclaration(version="1.0", encoding="utf-8")
