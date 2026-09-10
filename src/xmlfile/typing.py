"""Type aliases used across `xmlfile`."""

from __future__ import annotations

import os
from typing import Union

__all__ = ["PathLike", "Scalar"]

# XML stores strings. The base parser never coerces values to int/float/bool;
# that is the job of explicit helper functions (see the implementation plan,
# section 9 "Core scalar type").
Scalar = Union[str, None]

PathLike = Union[str, os.PathLike]
