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


# ===========================================================================
#  Standard hue-shifted builders (dec-0021): every sprite uses material ramps,
#  directional top-left light, and a selective outline via the shared Canvas.
# ===========================================================================
from .sprite import Canvas, outline_dark
from .shading import Ramp


def _icon(contract, cls="item_icon"):
    return Canvas(*contract.canvas_of(cls))


def build_sword(contract, materials=None):
    blade, gold, grip = Ramp((176, 184, 198)), Ramp((214, 176, 72)), Ramp((122, 80, 48))
    cv = _icon(contract)
    for i in range(9):                          # diagonal blade, bottom-left -> top-right
        r, c = 11 - i, 4 + i
        cv.px(r, c, blade.base); cv.px(r, c + 1, blade.shadow)
        cv.px(r - 1, c, blade.highlight)        # lit (top-left) edge
    cv.px(2, 12, blade.highlight)               # tip
    cv.rect(11, 12, 3, 6, gold.base); cv.px(11, 3, gold.highlight); cv.px(12, 6, gold.shadow)  # guard
    cv.rect(12, 14, 3, 4, grip.base); cv.px(14, 4, grip.shadow)     # grip
    cv.px(14, 3, gold.base)                     # pommel
    cv.outline(outline_dark((90, 90, 100)))
    return cv.array()


def build_potion(contract, materials=None):
    glass, liquid, cork = Ramp((198, 214, 226)), Ramp((214, 64, 78)), Ramp((132, 92, 56))
    cv = _icon(contract)
    cv.disc(10, 8, 4, 4, liquid.base)           # round flask of liquid
    cv.disc(11, 10, 2, 2, liquid.shadow)        # bottom-right shade
    cv.disc(9, 6, 1.4, 1.6, liquid.highlight)   # top-left sheen
    cv.rect(4, 6, 7, 9, glass.base)             # neck
    cv.px(4, 7, glass.highlight); cv.rect(4, 6, 9, 9, glass.shadow)
    cv.rect(6, 6, 5, 11, glass.base)            # shoulders/rim
    cv.rect(2, 3, 7, 9, cork.base); cv.px(3, 9, cork.shadow)        # cork
    cv.px(8, 6, glass.highlight)                # glass glint over liquid
    cv.outline(outline_dark((70, 80, 96)))
    return cv.array()


def build_key(contract, materials=None):
    gold = Ramp((226, 190, 74))
    cv = _icon(contract)
    cv.disc(5, 5, 3, 3, gold.base)              # bow (ring)
    cv.clear_disc(5, 5, 1.4, 1.4)
    cv.disc(4, 4, 1.2, 1.2, gold.highlight)     # top-left sheen on the bow
    cv.rect(6, 12, 6, 7, gold.base)             # shaft
    cv.rect(6, 12, 7, 7, gold.shadow)           # shaft right-shade
    cv.rect(11, 11, 8, 10, gold.base); cv.rect(12, 12, 8, 9, gold.base)   # teeth
    cv.px(12, 9, gold.shadow)
    cv.outline(outline_dark((150, 110, 30)))
    return cv.array()


def build_heart(contract, materials=None):
    red = Ramp((226, 62, 84))
    cv = Canvas(*contract.canvas_of("ui_element"))   # 16x16
    spans = {4: [(4, 6), (9, 11)], 5: [(3, 12)], 6: [(3, 12)], 7: [(4, 11)],
             8: [(5, 10)], 9: [(6, 9)], 10: [(7, 8)]}
    for r, segs in spans.items():                    # clean heart silhouette
        for c0, c1 in segs:
            cv.rect(r, r, c0, c1, red.base)
    for r, segs in spans.items():                    # shadow: bottom-right half
        if r >= 6:
            for c0, c1 in segs:
                cv.rect(r, r, max(c0, 8), c1, red.shadow)
    cv.rect(4, 5, 4, 5, red.highlight)               # glint on the top-left lobe
    cv.px(4, 4, (255, 240, 245))                      # specular dot
    cv.outline(outline_dark(red.base))
    return cv.array()


def build_coin(contract, materials=None):
    gold = Ramp((240, 206, 84))
    cv = Canvas(*contract.canvas_of("ui_element"))   # 16x16
    circ = {2: (6, 9), 3: (4, 11), 4: (3, 12), 5: (3, 12), 6: (2, 13), 7: (2, 13),
            8: (2, 13), 9: (2, 13), 10: (3, 12), 11: (3, 12), 12: (4, 11), 13: (6, 9)}
    for r, (c0, c1) in circ.items():                 # clean circle silhouette
        cv.rect(r, r, c0, c1, gold.base)
    for r in range(9, 14):                           # bottom-right shade
        c0, c1 = circ[r]
        cv.rect(r, r, (c0 + c1) // 2, c1, gold.shadow)
    cv.rect(3, 4, 4, 6, gold.highlight); cv.px(2, 7, gold.highlight)   # top-left rim
    cv.rect(6, 9, 6, 9, gold.shadow); cv.rect(7, 8, 7, 8, gold.base)   # inner face
    cv.px(4, 5, (255, 248, 210))                     # specular
    cv.outline(outline_dark((170, 130, 30)))
    return cv.array()


_RGBA_BUILDERS = {
    ("character", "player"): build_humanoid,   # LPC-style layered humanoid (dec-0022)
    ("enemy", "slime"): build_blob,            # blob creature archetype (default: green)
    ("item_icon", "sword"): build_sword,
    ("item_icon", "potion"): build_potion,
    ("item_icon", "key"): build_key,
    ("ui_element", "heart"): build_heart,
    ("ui_element", "coin"): build_coin,
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
