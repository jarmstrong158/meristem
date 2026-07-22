"""Agent-drawn backend: coordinate-based sprite builders using the shared
hue-shifted material-ramp standard (dec-0020/0021). Wins the *objects* (character,
enemy, icons, UI) per dec-0011; tiles fall back to the procedural backend.

Every builder draws from named materials, each auto-deriving a 3-shade ramp
(shadow cool / base / highlight warm) with one light direction (top-left) and a
selective outline. See sprite.py (the Canvas toolkit) and shading.py (the ramps).
"""
from __future__ import annotations

import numpy as np
from PIL import Image

from .base import AssetSpec, Generator
from .procedural import ProceduralGenerator
from .humanoid import build_humanoid, humanoid_walk
from .creatures import build_blob


from .items import weapon, consumable, pickup


# Each entry is a builder(contract) -> RGBA. Objects are archetype instances
# (humanoid/blob/weapon/consumable/pickup) parametrised by config (dec-0022);
# tiles fall back to the procedural backend.
_RGBA_BUILDERS = {
    ("character", "player"): build_humanoid,                          # LPC layered humanoid
    ("enemy", "slime"): build_blob,                                   # blob (default green)
    ("item_icon", "sword"): weapon,                                   # weapon(sword)
    ("item_icon", "potion"): consumable,                             # consumable(red)
    ("item_icon", "key"): lambda c: pickup(c, {"shape": "key", "color": (226, 190, 74)}),
    ("ui_element", "heart"): lambda c: pickup(c, {"shape": "heart", "color": (226, 62, 84)}),
    ("ui_element", "coin"): lambda c: pickup(c, {"shape": "coin", "color": (240, 206, 84)}),
}


class AgentDrawnGenerator(Generator):
    name = "agent-drawn"

    def __init__(self):
        self._proc = ProceduralGenerator()

    def supports(self, spec: AssetSpec) -> bool:
        return (spec.asset_class, spec.name) in _RGBA_BUILDERS or self._proc.supports(spec)

    def generate(self, spec: AssetSpec, contract) -> Image.Image:
        builder = _RGBA_BUILDERS.get((spec.asset_class, spec.name))
        if builder is not None:                                # hue-shifted RGBA sprite
            return Image.fromarray(builder(contract), "RGBA")
        return self._proc.generate(spec, contract)             # tiles reuse procedural

    def generate_frames(self, spec: AssetSpec, contract) -> list[Image.Image]:
        """Walk cycle via the humanoid's shared skeleton (dec-0022): each frame is a
        Pose the layers register to — see humanoid.py + docs/research/01-walk-cycle.md."""
        if spec.asset_class == "character" and spec.variant == "walk":
            return [Image.fromarray(a, "RGBA") for a in humanoid_walk(contract)]
        return [self.generate(spec, contract)]
