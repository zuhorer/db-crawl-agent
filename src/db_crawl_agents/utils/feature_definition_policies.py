from __future__ import annotations
from typing import List
import re
# from .schema import FeatureDefinitionSpecDraft
from ..contracts.feature_orchestrator.feature_orchestrator import Feature

_UPPER_SNAKE = re.compile(r"^[A-Z][A-Z0-9_]*$")

def _to_upper_snake(s: str) -> str:
    s = re.sub(r"[\s\-]+", "_", s).upper()
    s = re.sub(r"[^A-Z0-9_]", "", s)
    return s

def enforce_basic_policies(
    features: List[Feature],
    max_features: int = 5
) -> List[Feature]:
    # 1) cap count
    trimmed = features[:max_features]

    # 2) naming + id invariants + uniqueness
    seen = set()
    fixed: List[Feature] = []
    for f in trimmed:
        name = f.name.strip()
        if not _UPPER_SNAKE.match(name):
            name = _to_upper_snake(name)
        # ensure uniqueness (append suffix if collision)
        base = name
        if base in seen:
            i = 2
            name = f"{base}_{i}"
            while name in seen:
                i += 1
                name = f"{base}_{i}"
        seen.add(name)

        # enforce id
        fid = f"feat.{name}"

        fixed.append(
            Feature(
                **{
                    **f.model_dump(),
                    "name": name,
                    "id": fid,
                }
            )
        )
    return fixed