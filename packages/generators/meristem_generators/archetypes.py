"""The archetype registry — the spec-addressable sprite vocabulary (dec-0022).

A manifest entity/item declares a sprite as `{archetype, config}`; this maps the
archetype name to its builder + canvas class + optional animation frames. New
creatures and items are config over this fixed library, not new dispatch code —
the same principle as the mechanics archetypes (dec-0001).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

import numpy as np
from PIL import Image

from .creatures import (BEETLE_DEFAULT, BLOB_DEFAULT, FLYER_DEFAULT, GHOST_DEFAULT,
                        QUADRUPED_DEFAULT, RAPTOR_DEFAULT, SERPENT_DEFAULT, SPIDER_DEFAULT,
                        build_blob, build_ghost, build_quadruped, build_flyer,
                        build_serpent, build_spider, build_raptor, build_beetle,
                        blob_idle, ghost_idle, quadruped_idle, flyer_flap,
                        serpent_idle, spider_idle, raptor_idle, beetle_idle)
from .humanoid import DEFAULT_CONFIG as HUMANOID_DEFAULT
from .humanoid import build_humanoid, humanoid_walk
from .items import (CHEST_DEFAULT, CONSUMABLE_DEFAULT, PICKUP_DEFAULT, PROJECTILE_DEFAULT,
                    WEAPON_DEFAULT, chest, consumable, pickup, pickup_frames, projectile, weapon)
from .procedural import TILE_DEFAULT, build_tile, tile_options


def _tile_build(contract, config) -> np.ndarray:
    name = (config or {}).get("name", TILE_DEFAULT["name"])
    return build_tile(contract, name, **tile_options(name))


@dataclass(frozen=True)
class Archetype:
    asset_class: str                                   # the gate / canvas class
    build: Callable                                    # (contract, config) -> RGBA ndarray
    frames: Optional[Callable] = None                  # (contract, config) -> list[ndarray]
    # The SAME default-config dict the builder merges — not a copy. The catalog
    # derives each archetype's colour knobs from it, so the advertised vocabulary
    # cannot drift from what the builder actually reads.
    defaults: dict = field(default_factory=dict)


ARCHETYPES: dict[str, Archetype] = {
    "humanoid":   Archetype("character", build_humanoid, humanoid_walk, HUMANOID_DEFAULT),
    "blob":       Archetype("enemy", build_blob, blob_idle, BLOB_DEFAULT),
    "ghost":      Archetype("enemy", build_ghost, ghost_idle, GHOST_DEFAULT),
    "quadruped":  Archetype("enemy", build_quadruped, quadruped_idle, QUADRUPED_DEFAULT),
    "flyer":      Archetype("enemy", build_flyer, flyer_flap, FLYER_DEFAULT),
    "serpent":    Archetype("enemy", build_serpent, serpent_idle, SERPENT_DEFAULT),
    "spider":     Archetype("enemy", build_spider, spider_idle, SPIDER_DEFAULT),
    "raptor":     Archetype("enemy", build_raptor, raptor_idle, RAPTOR_DEFAULT),
    "beetle":     Archetype("enemy", build_beetle, beetle_idle, BEETLE_DEFAULT),
    "weapon":     Archetype("item_icon", weapon, None, WEAPON_DEFAULT),
    "consumable": Archetype("item_icon", consumable, None, CONSUMABLE_DEFAULT),
    "pickup":     Archetype("item_icon", pickup, pickup_frames, PICKUP_DEFAULT),
    "chest":      Archetype("item_icon", chest, None, CHEST_DEFAULT),
    "projectile": Archetype("item_icon", projectile, None, PROJECTILE_DEFAULT),
    "tile":       Archetype("terrain_tile", _tile_build, None, TILE_DEFAULT),
}


def archetype_defaults(name: str) -> dict:
    """The default config a builder merges for `name` (a copy; safe to mutate)."""
    return dict(_get(name).defaults)


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
