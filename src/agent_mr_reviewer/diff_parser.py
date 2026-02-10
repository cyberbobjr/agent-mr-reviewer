from __future__ import annotations

from unidiff import PatchSet


def parse_diff(diff_text: str) -> PatchSet:
    return PatchSet(diff_text)
