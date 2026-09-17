"""Type aliases used across `xmlfile`."""

from __future__ import annotations

import os

__all__ = ["PathLike", "Scalar"]

# XML stores strings. The base parser never coerces values to int/float/bool;
# that is the job of explicit helper functions (see the implementation plan,
# section 9 "Core scalar type").
Scalar = str | None

PathLike = str | os.PathLike[str]
