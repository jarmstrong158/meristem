"""The archetype registry — the spec-addressable sprite vocabulary (dec-0022).

A manifest entity/item declares a sprite as `{archetype, config}`; this maps the
archetype name to its builder + canvas class + optional animation frames. New
creatures and items are config over this fixed library, not new dispatch code —
the same principle as the mechanics archetypes (dec-0001).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np
from PIL import Image

from .creatures import (build_blob, build_ghost, build_quadruped, build_flyer,
                        build_serpent, build_spider, blob_idle, ghost_idle,
                        quadruped_idle, flyer_flap, serpent_idle, spider_idle)
from .humanoid import build_humanoid, humanoid_walk
from .items import chest, consumable, pickup, pickup_frames, projectile, weapon
from .procedural import ProceduralGenerator, build_tile


def _tile_build(contract, config) -> np.ndarray:
    name = (config or {}).get("name", "grass")
    opts = ProceduralGenerator._TILES.get(name, {})
    return build_tile(contract, name, **opts)


@dataclass(frozen=True)
class Archetype:
    asset_class: str                                   # the gate / canvas class
    build: Callable                                    # (contract, config) -> RGBA ndarray
    frames: Optional[Callable] = None                  # (contract, config) -> list[ndarray]


ARCHETYPES: dict[str, Archetype] = {
    "humanoid":   Archetype("character", build_humanoid, humanoid_walk),
    "blob":       Archetype("enemy", build_blob, blob_idle),
    "ghost":      Archetype("enemy", build_ghost, ghost_idle),
    "quadruped":  Archetype("enemy", build_quadruped, quadruped_idle),
    "flyer":      Archetype("enemy", build_flyer, flyer_flap),
    "serpent":    Archetype("enemy", build_serpent, serpent_idle),
    "spider":     Archetype("enemy", build_spider, spider_idle),
    "weapon":     Archetype("item_icon", weapon),
    "consumable": Archetype("item_icon", consumable),
    "pickup":     Archetype("item_icon", pickup, pickup_frames),
    "chest":      Archetype("item_icon", chest),
    "projectile": Archetype("item_icon", projectile),
    "tile":       Archetype("terrain_tile", _tile_build),
}


def known_archetypes() -> list[str]:
    return sorted(ARCHETYPES)


def archetype_class(name: str) -> str:
    return _get(name).asset_class


def build_archetype(contract, name: str, config: dict | None = None) -> Image.Image:
    return Image.fromarray(_get(name).build(contract, config or {}), "RGBA")


def archetype_frames(contract, name: str, config: dict | None = None) -> Optional[list[Image.Image]]:
    a = _get(name)
    if a.frames is None:
        return None
    frames = a.frames(contract, config or {})       # a frame fn may itself opt out (None)
    if not frames:
        return None
    return [Image.fromarray(f, "RGBA") for f in frames]


def _get(name: str) -> Archetype:
    if name not in ARCHETYPES:
        raise KeyError(f"unknown archetype {name!r}; known: {known_archetypes()}")
    return ARCHETYPES[name]
