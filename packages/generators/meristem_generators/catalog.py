"""The sprite vocabulary as data — what an author can actually pick.

The archetype library (dec-0022) is spec-addressable, but a manifest author (or the
LLM writing one) needs to *discover* it: which archetypes exist, what `build`/`kind`/
`shape` each takes, which config knobs it accepts. This module surfaces that as a
catalog, and validates a sprite descriptor's variant against it — closing the gap
where `{archetype: flyer, config: {build: "dragon"}}` passes the schema enum but
silently falls back to the default build.

Variant options are sourced from the actual build tables, so the catalog cannot
drift from the builders.
"""
from __future__ import annotations

from .archetypes import ARCHETYPES, archetype_class, known_archetypes
from .creatures import (BLOB_BUILDS, _FLYER_BUILDS, _GHOSTS, _QUAD_BUILDS,
                        _SERPENT_BUILDS, _SPIDER_BUILDS, _RAPTOR_BUILDS, _BEETLE_BUILDS)
from .humanoid import (_ACCENTS, _ARMS, _BEARDS, _FEET, _GARMENTS, _HAIR,
                       _HATS, _HELD)
from .items import _CHEST_BUILDS, _CONS, _PICKUPS, _PROJECTILES, _WEAPONS
from .procedural import known_tiles

# variant axes per archetype: {archetype: {config_key: [allowed options]}}
_VARIANTS: dict[str, dict[str, list[str]]] = {
    "humanoid":   {"hair_style": sorted(_HAIR), "hat": sorted(_HATS), "beard": sorted(_BEARDS),
                   "held": sorted(_HELD), "garment": sorted(_GARMENTS), "feet": sorted(_FEET),
                   "arms": sorted(_ARMS), "hair_accent": sorted(_ACCENTS)},
    "blob":       {"build": list(BLOB_BUILDS), "size": ["s", "m", "l"]},
    "ghost":      {"build": sorted(_GHOSTS)},
    "quadruped":  {"build": sorted(_QUAD_BUILDS)},
    "flyer":      {"build": sorted(_FLYER_BUILDS)},
    "serpent":    {"build": sorted(_SERPENT_BUILDS)},
    "spider":     {"build": sorted(_SPIDER_BUILDS)},
    "raptor":     {"build": sorted(_RAPTOR_BUILDS)},
    "beetle":     {"build": sorted(_BEETLE_BUILDS)},
    "weapon":     {"kind": sorted(_WEAPONS)},
    "consumable": {"shape": sorted(_CONS)},
    "pickup":     {"shape": sorted(_PICKUPS)},
    "projectile": {"kind": sorted(_PROJECTILES)},
    "chest":      {"build": sorted(_CHEST_BUILDS)},
    "tile":       {"name": known_tiles()},
}


def _is_rgb(value) -> bool:
    """A config default that is an RGB(A) triple/quad of 0-255 ints — i.e. a colour knob."""
    return (isinstance(value, (tuple, list)) and len(value) in (3, 4)
            and all(isinstance(c, int) and not isinstance(c, bool) and 0 <= c <= 255
                    for c in value))


def color_keys(archetype: str) -> list[str]:
    """The freeform colour knobs an archetype accepts, DERIVED from the default config
    its builder merges (every default that is an RGB triple is a colour knob).

    This used to be a hand-maintained table, and it drifted: `raptor` and `beetle`
    were added to the registry but never to the table, so `list_sprite_archetypes`
    told authors they had no colour knob even though both builders read cfg["color"].
    Deriving it means adding a builder cannot silently under-report its vocabulary."""
    a = ARCHETYPES.get(archetype)
    if a is None:
        return []
    return sorted(k for k, v in a.defaults.items() if _is_rgb(v))


# freeform RGB/material knobs per archetype (for discoverability; not enumerable)
_COLOR_KEYS: dict[str, list[str]] = {name: color_keys(name) for name in ARCHETYPES}

_ANIMATED = {name for name, a in ARCHETYPES.items() if a.frames is not None}


def sprite_catalog() -> list[dict]:
    """The full pickable vocabulary: one entry per archetype with its class, whether
    it animates, its variant axes + options, and its colour knobs."""
    out = []
    for name in known_archetypes():
        out.append({
            "archetype": name,
            "class": archetype_class(name),
            "animated": name in _ANIMATED,
            "variants": _VARIANTS.get(name, {}),
            "color_keys": color_keys(name),
        })
    return out


def validate_sprite(archetype: str, config: dict | None = None) -> list[str]:
    """Problems with a sprite descriptor ([] = ok). Beyond the schema's archetype
    enum: each variant value (build/kind/shape/...) must be a known option, so a
    typo'd build is a validation error rather than a silent fallback to the default."""
    if archetype not in ARCHETYPES:
        return [f"unknown sprite archetype {archetype!r}; known: {known_archetypes()}"]
    cfg = config or {}
    problems = []
    for key, options in _VARIANTS.get(archetype, {}).items():
        if key in cfg and cfg[key] not in options:
            problems.append(f"{archetype}.{key}={cfg[key]!r} is not a known option {options}")
    return problems
