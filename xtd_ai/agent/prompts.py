"""System prompt loader (pure Python)."""

from __future__ import annotations

from functools import cache
from pathlib import Path


@cache
def load_system_prompt(name: str = "system_es.md") -> str:
    return (
        (Path(__file__).parent / "prompts" / name).read_text(encoding="utf-8").strip()
    )
