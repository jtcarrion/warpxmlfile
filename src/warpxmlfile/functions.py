"""The public functions of `warpxmlfile`: read, write, to_string, from_string."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .models import WarpTiltSeries

if TYPE_CHECKING:
    from ._xml.typing import PathLike

__all__ = ["from_string", "read", "to_string", "write"]


def read(filename: PathLike) -> WarpTiltSeries:
    """Read a Warp / M tilt-series XML file.

    Parameters
    ----------
    filename
        Path to the file. The document is kept with the returned model so that
        `write` reproduces every byte that was not edited.
    """
    return WarpTiltSeries.from_file(filename)


def from_string(text: str) -> WarpTiltSeries:
    """Parse a Warp / M tilt-series XML held in a string.

    Parameters
    ----------
    text
        The XML source.
    """
    return WarpTiltSeries.from_string(text)


def to_string(tilt_series: WarpTiltSeries) -> str:
    """Serialise a `WarpTiltSeries` to XML text.

    Parameters
    ----------
    tilt_series
        The model to serialise. If it was read from a file, only the elements
        whose values changed are re-generated; everything else is reproduced
        byte for byte. A model built from scratch is written in Warp's layout.
    """
    return tilt_series.to_string()


def write(
    tilt_series: WarpTiltSeries, filename: PathLike, *, overwrite: bool = True
) -> None:
    """Write a `WarpTiltSeries` to a file.

    Parameters
    ----------
    tilt_series
        The model to write; see `to_string` for what is re-generated.
    filename
        Destination path.
    overwrite
        Whether an existing file may be replaced. True by default, like
        `starfile` and `mdocfile`.
    """
    tilt_series.to_file(filename, overwrite=overwrite)
