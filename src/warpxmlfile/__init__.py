"""Read and write Warp / M tilt-series XML files in Python."""

from __future__ import annotations

from .functions import from_string, read, to_string, write
from .models import Grid, WarpTiltSeries

__all__ = ["Grid", "WarpTiltSeries", "from_string", "read", "to_string", "write"]

try:  # pragma: no cover - depends on install method
    from importlib.metadata import PackageNotFoundError, version

    __version__ = version("warpxmlfile")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.0.dev0"
