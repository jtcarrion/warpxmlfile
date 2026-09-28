"""Type aliases used across `xmlfile`."""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any

__all__ = ["PathLike", "Scalar", "ValueFormat"]

# XML stores strings. The base parser never coerces values to int/float/bool;
# that is the job of explicit helper functions (see the implementation plan,
# section 9 "Core scalar type").
Scalar = str | None

PathLike = str | os.PathLike[str]

# How helper functions format numbers when writing: the name of the built-in
# float32 formatter, a ``%``/``{}`` format string, or a callable.
ValueFormat = str | Callable[[Any], str]
