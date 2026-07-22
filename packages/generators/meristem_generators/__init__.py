"""Meristem generators: the spec-addressable archetype library.

Assets are built by ARCHETYPE + config (`build_archetype`); the legacy name-based
Generator backends remain for the bake-off and internal use.
"""
from .base import AssetSpec, Generator
from .registry import available, get, register
from .procedural import ProceduralGenerator
from .agent_drawn import AgentDrawnGenerator
from .archetypes import (ARCHETYPES, archetype_class, archetype_frames, build_archetype,
                         known_archetypes)

register(ProceduralGenerator())
register(AgentDrawnGenerator())

__all__ = ["AssetSpec", "Generator", "ProceduralGenerator", "AgentDrawnGenerator",
           "register", "get", "available",
           "ARCHETYPES", "archetype_class", "archetype_frames", "build_archetype",
           "known_archetypes"]
