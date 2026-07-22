"""Backend registry. A new backend (paid API, CC0-LoRA diffusion) registers here
and is usable everywhere without touching the gate or the compiler."""
from __future__ import annotations

from .base import Generator

_REGISTRY: dict[str, Generator] = {}


def register(gen: Generator) -> Generator:
    _REGISTRY[gen.name] = gen
    return gen


def get(name: str) -> Generator:
    if name not in _REGISTRY:
        raise KeyError(f"no generator {name!r}; registered: {sorted(_REGISTRY)}")
    return _REGISTRY[name]


def available() -> list[str]:
    return sorted(_REGISTRY)
