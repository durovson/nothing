from __future__ import annotations

import sys
from collections.abc import Sequence

from app.core.constants import MAX_PYTHON, MIN_PYTHON


def ensure_supported_python(version_info: Sequence[int] = sys.version_info) -> None:
    version = tuple(version_info[:3])
    if not MIN_PYTHON <= version <= MAX_PYTHON:
        detected = ".".join(map(str, version))
        raise RuntimeError(
            f"Unsupported Python {detected}; Gift Guarant requires Python 3.14.0-3.14.3 "
            "and is deployed on Python 3.14.3."
        )

