"""Meristem generators: pluggable asset backends behind `generate(spec, contract) -> Image`."""
from .base import AssetSpec, Generator
from .registry import available, get, register
from .procedural import ProceduralGenerator
from .agent_drawn import AgentDrawnGenerator

register(ProceduralGenerator())
register(AgentDrawnGenerator())

__all__ = ["AssetSpec", "Generator", "ProceduralGenerator", "AgentDrawnGenerator",
           "register", "get", "available"]
