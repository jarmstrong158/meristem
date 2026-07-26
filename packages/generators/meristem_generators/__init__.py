"""Meristem generators: the spec-addressable archetype library.

Assets are built by ARCHETYPE + config (`build_archetype`); the legacy name-based
Generator backends remain for the bake-off and internal use.
"""
from .base import AssetSpec, Generator
from .registry import available, get, register
from .procedural import ProceduralGenerator, TILES, known_tiles, tile_options
from .agent_drawn import AgentDrawnGenerator
from .archetypes import (ARCHETYPES, archetype_class, archetype_defaults, archetype_frames,
                         build_archetype, known_archetypes)
from .catalog import (color_keys, config_keys, sprite_catalog, sprite_warnings,
                      validate_sprite)
from .preview import render_builds, render_sprite, variant_key

register(ProceduralGenerator())
register(AgentDrawnGenerator())

__all__ = ["AssetSpec", "Generator", "ProceduralGenerator", "AgentDrawnGenerator",
           "register", "get", "available",
           "TILES", "known_tiles", "tile_options",
           "ARCHETYPES", "archetype_class", "archetype_defaults", "archetype_frames",
           "build_archetype", "known_archetypes",
           "color_keys", "config_keys", "sprite_catalog", "sprite_warnings",
           "validate_sprite",
           "render_builds", "render_sprite", "variant_key"]
