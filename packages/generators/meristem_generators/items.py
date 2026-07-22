"""Item / prop archetypes (dec-0022): weapon, consumable, pickup.

Parametric recipes, not per-name builders — a health potion and a mana potion are
`consumable(liquid=red)` / `consumable(liquid=blue)`, a dagger is `weapon(kind=dagger)`.
Built to the sprite standard (dec-0021): material ramps, top-left light, sel-out.
"""
from __future__ import annotations

import numpy as np

from .shading import Ramp
from .sprite import Canvas, outline_dark

_STEEL, _GOLD, _LEATHER, _WOOD = (176, 184, 198), (214, 176, 72), (122, 80, 48), (124, 84, 46)


def _icon(contract, cls="item_icon") -> Canvas:
    return Canvas(*contract.canvas_of(cls))


# ------------------------------- weapon -----------------------------------
def _vblade(cv, blade, c0, c1, r_top, r_bot, tip=True):
    """A vertical blade: lit left edge, base, shadow right edge, pointed tip."""
    if tip:
        cv.px(r_top, (c0 + c1) // 2, blade.highlight)
        r_top += 1
    for c in range(c0, c1 + 1):
        shade = blade.highlight if c == c0 else (blade.shadow if c == c1 else blade.base)
        cv.rect(r_top, r_bot, c, c, shade)


def _guard(cv, gold, r, c0, c1):
    cv.rect(r, r, c0, c1, gold.base)
    cv.px(r, c0, gold.highlight); cv.px(r, c1, gold.shadow)


def _grip(cv, grip, gold, c0, c1, r0, r1):
    cv.rect(r0, r1, c0, c1, grip.base); cv.rect(r0, r1, c1, c1, grip.shadow)
    cv.rect(r1 + 1, r1 + 1, c0, c1, gold.base)              # pommel


def _wp_sword(cv, blade, gold, grip, wood, orb, big=False):
    if big:                                                  # greatsword
        _vblade(cv, blade, 6, 9, 1, 10)
        _guard(cv, gold, 11, 3, 12); cv.rect(12, 12, 4, 11, gold.shadow)
        _grip(cv, grip, gold, 7, 8, 12, 14)
    else:                                                    # sword
        _vblade(cv, blade, 6, 8, 2, 10)
        _guard(cv, gold, 11, 4, 11)
        _grip(cv, grip, gold, 6, 8, 12, 13)


def _wp_dagger(cv, blade, gold, grip, wood, orb):
    _vblade(cv, blade, 7, 8, 4, 9)
    _guard(cv, gold, 10, 5, 10)
    _grip(cv, grip, gold, 7, 8, 11, 12)


def _wp_axe(cv, blade, gold, grip, wood, orb):
    cv.rect(2, 14, 7, 8, wood.base); cv.rect(2, 14, 8, 8, wood.shadow)   # haft
    # axe head: a curved wedge on the upper-left
    head = {2: (3, 6), 3: (2, 6), 4: (2, 6), 5: (3, 6)}
    for r, (c0, c1) in head.items():
        cv.rect(r, r, c0, c1, blade.base)
    cv.rect(2, 3, 3, 4, blade.highlight); cv.rect(4, 5, 2, 3, blade.shadow)
    cv.rect(2, 5, 9, 10, blade.base); cv.rect(3, 4, 10, 10, blade.shadow)  # small back spike
    cv.px(14, 8, gold.base)


def _wp_spear(cv, blade, gold, grip, wood, orb):
    cv.rect(4, 15, 7, 8, wood.base); cv.rect(4, 15, 8, 8, wood.shadow)   # shaft
    head = {1: (7, 7), 2: (6, 8), 3: (6, 8), 4: (6, 8), 5: (7, 7)}       # leaf tip
    for r, (c0, c1) in head.items():
        cv.rect(r, r, c0, c1, blade.base)
    cv.rect(2, 4, 6, 6, blade.highlight); cv.rect(2, 4, 8, 8, blade.shadow)
    cv.rect(5, 5, 5, 10, gold.base)                          # collar


def _wp_staff(cv, blade, gold, grip, wood, orb):
    cv.rect(4, 15, 7, 8, wood.base); cv.rect(4, 15, 8, 8, wood.shadow)   # shaft
    o = Ramp(orb)
    cv.disc(4, 7, 3, 3, o.base)                              # orb
    cv.disc(3, 6, 1.3, 1.3, o.highlight)
    cv.disc(5, 8, 1.4, 1.4, o.shadow)
    cv.px(2, 6, (255, 255, 255))                             # glint


_WEAPONS = {
    "sword": lambda cv, b, g, gr, w, o: _wp_sword(cv, b, g, gr, w, o),
    "dagger": _wp_dagger,
    "greatsword": lambda cv, b, g, gr, w, o: _wp_sword(cv, b, g, gr, w, o, big=True),
    "axe": _wp_axe,
    "spear": _wp_spear,
    "staff": _wp_staff,
}


def weapon(contract, config=None) -> np.ndarray:
    cfg = {"kind": "sword", "blade": _STEEL, "hilt": _GOLD, "grip": _LEATHER,
           "wood": _WOOD, "orb": (90, 200, 230)}
    cfg.update(config or {})
    cv = _icon(contract)
    blade, gold, grip, wood = Ramp(cfg["blade"]), Ramp(cfg["hilt"]), Ramp(cfg["grip"]), Ramp(cfg["wood"])
    _WEAPONS.get(cfg["kind"], _WEAPONS["sword"])(cv, blade, gold, grip, wood, cfg["orb"])
    cv.outline(outline_dark((70, 72, 82)))
    return cv.array()


# ----------------------------- consumable ---------------------------------
def consumable(contract, config=None) -> np.ndarray:
    cfg = {"liquid": (214, 64, 78), "glass": (198, 214, 226), "cork": (132, 92, 56)}
    cfg.update(config or {})
    liquid, glass, cork = Ramp(cfg["liquid"]), Ramp(cfg["glass"]), Ramp(cfg["cork"])
    cv = _icon(contract)
    cv.disc(10, 8, 4, 4, liquid.base)                        # round flask of liquid
    cv.disc(11, 10, 2, 2, liquid.shadow)                     # bottom-right shade
    cv.disc(9, 6, 1.4, 1.6, liquid.highlight)                # top-left sheen
    cv.rect(4, 6, 7, 9, glass.base)                          # neck
    cv.px(4, 7, glass.highlight); cv.rect(4, 6, 9, 9, glass.shadow)
    cv.rect(6, 6, 5, 11, glass.base)                         # shoulders/rim
    cv.rect(2, 3, 7, 9, cork.base); cv.px(3, 9, cork.shadow)  # cork
    cv.px(8, 6, glass.highlight)                             # glass glint over liquid
    cv.outline(outline_dark((70, 80, 96)))
    return cv.array()


# ------------------------------- pickup -----------------------------------
def _pickup_coin(cv, color):
    gold = Ramp(color)
    circ = {2: (6, 9), 3: (4, 11), 4: (3, 12), 5: (3, 12), 6: (2, 13), 7: (2, 13),
            8: (2, 13), 9: (2, 13), 10: (3, 12), 11: (3, 12), 12: (4, 11), 13: (6, 9)}
    for r, (c0, c1) in circ.items():
        cv.rect(r, r, c0, c1, gold.base)
    for r in range(9, 14):
        c0, c1 = circ[r]; cv.rect(r, r, (c0 + c1) // 2, c1, gold.shadow)
    cv.rect(3, 4, 4, 6, gold.highlight); cv.px(2, 7, gold.highlight)
    cv.rect(6, 9, 6, 9, gold.shadow); cv.rect(7, 8, 7, 8, gold.base)
    cv.px(4, 5, (255, 248, 210))
    cv.outline(outline_dark(color))


def _pickup_heart(cv, color):
    red = Ramp(color)
    spans = {4: [(4, 6), (9, 11)], 5: [(3, 12)], 6: [(3, 12)], 7: [(4, 11)],
             8: [(5, 10)], 9: [(6, 9)], 10: [(7, 8)]}
    for r, segs in spans.items():
        for c0, c1 in segs:
            cv.rect(r, r, c0, c1, red.base)
    for r, segs in spans.items():
        if r >= 6:
            for c0, c1 in segs:
                cv.rect(r, r, max(c0, 8), c1, red.shadow)
    cv.rect(4, 5, 4, 5, red.highlight); cv.px(4, 4, (255, 240, 245))
    cv.outline(outline_dark(color))


def _pickup_key(cv, color):
    gold = Ramp(color)
    cv.disc(5, 5, 3, 3, gold.base); cv.clear_disc(5, 5, 1.4, 1.4)
    cv.disc(4, 4, 1.2, 1.2, gold.highlight)
    cv.rect(6, 12, 6, 7, gold.base); cv.rect(6, 12, 7, 7, gold.shadow)
    cv.rect(11, 11, 8, 10, gold.base); cv.rect(12, 12, 8, 9, gold.base)
    cv.px(12, 9, gold.shadow)
    cv.outline(outline_dark(color))


def _pickup_gem(cv, color):
    gem = Ramp(color)
    spans = {3: (6, 9), 4: (5, 10), 5: (4, 11), 6: (3, 12), 7: (4, 11),
             8: (5, 10), 9: (6, 9), 10: (7, 8)}                     # faceted diamond
    for r, (c0, c1) in spans.items():
        cv.rect(r, r, c0, c1, gem.base)
    for r, (c0, c1) in spans.items():                              # right facet in shadow
        cv.rect(r, r, (c0 + c1) // 2 + 1, c1, gem.shadow)
    cv.rect(3, 5, 6, 7, gem.highlight); cv.px(3, 6, (255, 255, 255))   # lit left facet + glint
    cv.outline(outline_dark(color))


_PICKUPS = {"coin": _pickup_coin, "heart": _pickup_heart, "key": _pickup_key, "gem": _pickup_gem}


def pickup(contract, config=None) -> np.ndarray:
    cfg = {"shape": "coin", "color": (240, 206, 84)}
    cfg.update(config or {})
    cls = "ui_element" if cfg["shape"] in ("coin", "heart") else "item_icon"
    cv = _icon(contract, cls)
    _PICKUPS.get(cfg["shape"], _pickup_coin)(cv, cfg["color"])
    return cv.array()
