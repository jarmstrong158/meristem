"""Item / prop archetypes (dec-0022): weapon, consumable, pickup.

Parametric recipes, not per-name builders — a health potion and a mana potion are
`consumable(liquid=red)` / `consumable(liquid=blue)`, a dagger is `weapon(kind=dagger)`.
Built to the sprite standard (dec-0021): material ramps, top-left light, sel-out.
"""
from __future__ import annotations

import numpy as np

from .shading import Ramp
from .sprite import Canvas, outline_dark, squeeze_h

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


def _wp_bow(cv, blade, gold, grip, wood, orb):
    limb = {2: 8, 3: 6, 4: 5, 5: 4, 6: 4, 7: 4, 8: 4, 9: 4, 10: 5, 11: 6, 12: 7, 13: 9}
    for r, c in limb.items():                                # curved wooden limb (bulges left)
        cv.px(r, c, wood.base); cv.px(r, c + 1, wood.shadow)
    cv.rect(3, 12, 8, 8, blade.highlight)                    # taut bowstring
    cv.rect(7, 8, 5, 11, wood.base); cv.px(8, 5, wood.shadow)   # nocked arrow shaft
    cv.rect(6, 8, 11, 13, blade.base)                        # arrowhead
    cv.px(6, 13, blade.highlight); cv.px(8, 13, blade.shadow)


def _wp_mace(cv, blade, gold, grip, wood, orb):
    cv.rect(8, 14, 7, 8, grip.base); cv.rect(8, 14, 8, 8, grip.shadow)   # handle
    cv.rect(14, 14, 7, 8, gold.base)                         # pommel
    cv.disc(5, 8, 3, 3, blade.base)                          # spiked head
    cv.disc(4, 7, 1.3, 1.3, blade.highlight); cv.disc(6, 9, 1.4, 1.4, blade.shadow)
    for r, c in [(1, 7), (1, 8), (2, 3), (3, 12), (5, 2), (5, 13), (8, 4), (8, 12)]:
        cv.px(r, c, blade.base)                              # radiating spikes
    cv.px(1, 7, blade.highlight)


def _wp_wand(cv, blade, gold, grip, wood, orb):
    cv.rect(6, 14, 7, 8, wood.base); cv.rect(6, 14, 8, 8, wood.shadow)   # short rod
    o = Ramp(orb)
    cv.disc(4, 8, 2.4, 2.4, o.base)                          # gem tip
    cv.disc(3, 7, 1.1, 1.1, o.highlight); cv.disc(5, 9, 1.1, 1.1, o.shadow)
    cv.px(2, 8, (255, 255, 255))                             # core glint
    cv.px(3, 11, (255, 255, 210)); cv.px(7, 11, (255, 255, 210))   # magic sparkles


_WEAPONS = {
    "sword": lambda cv, b, g, gr, w, o: _wp_sword(cv, b, g, gr, w, o),
    "dagger": _wp_dagger,
    "greatsword": lambda cv, b, g, gr, w, o: _wp_sword(cv, b, g, gr, w, o, big=True),
    "axe": _wp_axe,
    "spear": _wp_spear,
    "staff": _wp_staff,
    "bow": _wp_bow,
    "mace": _wp_mace,
    "wand": _wp_wand,
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
def _cons_flask(cv, liquid, glass, cork):
    cv.disc(10, 8, 4, 4, liquid.base)                        # round flask of liquid
    cv.disc(11, 10, 2, 2, liquid.shadow)
    cv.disc(9, 6, 1.4, 1.6, liquid.highlight)
    cv.rect(4, 6, 7, 9, glass.base); cv.px(4, 7, glass.highlight); cv.rect(4, 6, 9, 9, glass.shadow)
    cv.rect(6, 6, 5, 11, glass.base)                         # shoulders/rim
    cv.rect(2, 3, 7, 9, cork.base); cv.px(3, 9, cork.shadow)
    cv.px(8, 6, glass.highlight)


def _cons_bottle(cv, liquid, glass, cork):
    cv.rect(6, 14, 5, 10, glass.base)                        # tall body
    cv.rect(9, 14, 5, 10, liquid.base)                       # liquid (lower)
    cv.rect(9, 14, 10, 10, liquid.shadow); cv.px(10, 5, liquid.highlight)
    cv.rect(6, 8, 6, 9, glass.shadow); cv.px(6, 6, glass.highlight)   # glass above liquid
    cv.rect(4, 6, 7, 8, glass.base)                          # neck
    cv.rect(2, 3, 6, 9, cork.base); cv.px(3, 9, cork.shadow)  # cork
    cv.px(11, 6, (255, 255, 255))                            # specular


def _cons_vial(cv, liquid, glass, cork):
    cv.rect(7, 14, 7, 9, glass.base)                         # thin tube
    cv.rect(10, 14, 7, 9, liquid.base); cv.rect(10, 14, 9, 9, liquid.shadow)
    cv.px(11, 7, liquid.highlight)
    cv.rect(5, 6, 7, 9, cork.base); cv.px(6, 9, cork.shadow)  # stopper
    cv.px(8, 7, glass.highlight)


def _cons_scroll(cv, liquid, glass, cork):
    cv.rect(6, 10, 4, 11, glass.base)                        # parchment sheet
    cv.rect(6, 6, 4, 11, glass.highlight)                    # lit top edge
    cv.rect(10, 10, 4, 11, glass.shadow)                     # shaded bottom edge
    cv.rect(8, 8, 5, 7, glass.shadow); cv.rect(8, 8, 9, 10, glass.shadow)   # lines of writing
    cv.rect(4, 12, 3, 4, cork.base); cv.rect(4, 12, 11, 12, cork.base)      # rolled rods (l/r)
    cv.rect(4, 12, 4, 4, cork.shadow); cv.rect(4, 12, 11, 11, cork.highlight)
    cv.rect(7, 9, 7, 8, liquid.base)                         # wax seal / ribbon


def _cons_pouch(cv, liquid, glass, cork):
    cv.disc(10, 8, 4, 4.5, cork.base)                        # leather sack
    cv.disc(12, 9, 2.4, 3, cork.shadow)                      # lower-right shade
    cv.disc(8, 6, 1.6, 1.8, cork.highlight)                  # top-left sheen
    cv.rect(5, 6, 6, 10, cork.base)                          # gathered neck
    cv.rect(5, 5, 6, 10, cork.shadow)                        # drawstring tie
    cv.px(4, 6, cork.base); cv.px(4, 10, cork.base)          # string ends
    cv.px(9, 8, (240, 214, 120)); cv.px(10, 7, (240, 214, 120))   # coin glint inside


_CONS = {"flask": _cons_flask, "bottle": _cons_bottle, "vial": _cons_vial,
         "scroll": _cons_scroll, "pouch": _cons_pouch}


def consumable(contract, config=None) -> np.ndarray:
    cfg = {"shape": "flask", "liquid": (214, 64, 78), "glass": (198, 214, 226), "cork": (132, 92, 56)}
    cfg.update(config or {})
    cv = _icon(contract)
    _CONS.get(cfg["shape"], _cons_flask)(cv, Ramp(cfg["liquid"]), Ramp(cfg["glass"]), Ramp(cfg["cork"]))
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


def _pickup_ring(cv, color):
    gold = Ramp(color)
    cv.disc(10, 8, 3.6, 3.6, gold.base); cv.clear_disc(10, 8, 1.8, 1.8)   # band
    cv.disc(9, 6, 1.3, 1.3, gold.highlight)
    cv.rect(11, 13, 6, 10, gold.shadow)                                   # lower-front shade
    g = Ramp((90, 200, 230))                                             # set gemstone
    cv.disc(4, 8, 2, 2, g.base); cv.px(3, 7, (255, 255, 255)); cv.px(5, 9, g.shadow)
    cv.outline(outline_dark(color))


def _pickup_skull(cv, color):
    bone = Ramp((222, 220, 202))
    dk = (46, 44, 52)
    cv.disc(7, 8, 4, 4, bone.base)                                        # cranium
    cv.rect(11, 13, 5, 11, bone.base); cv.rect(13, 13, 6, 10, bone.base)  # jaw
    cv.rect(5, 6, 5, 7, bone.highlight)                                   # lit brow
    cv.rect(6, 8, 5, 6, dk); cv.rect(6, 8, 10, 11, dk)                    # eye sockets
    cv.px(10, 8, dk); cv.px(10, 9, dk)                                    # nasal cavity
    for c in (7, 9, 11):
        cv.px(13, c, dk)                                                  # teeth gaps
    cv.outline(outline_dark((222, 220, 202)))


def _pickup_star(cv, color):
    st = Ramp(color)
    cv.rect(2, 13, 7, 8, st.base)                                         # vertical spoke
    cv.rect(7, 8, 3, 12, st.base)                                         # horizontal spoke
    cv.disc(7, 8, 2.6, 2.6, st.base)                                      # hub
    cv.rect(4, 6, 6, 7, st.highlight); cv.px(3, 7, (255, 255, 255))       # sheen + glint
    cv.rect(9, 11, 8, 9, st.shadow)                                       # lower-right shade
    cv.outline(outline_dark(color))


_PICKUPS = {"coin": _pickup_coin, "heart": _pickup_heart, "key": _pickup_key,
            "gem": _pickup_gem, "ring": _pickup_ring, "skull": _pickup_skull, "star": _pickup_star}


def pickup(contract, config=None) -> np.ndarray:
    cfg = {"shape": "coin", "color": (240, 206, 84)}
    cfg.update(config or {})
    cls = "ui_element" if cfg["shape"] in ("coin", "heart") else "item_icon"
    cv = _icon(contract, cls)
    _PICKUPS.get(cfg["shape"], _pickup_coin)(cv, cfg["color"])
    return cv.array()


def coin_spin(contract, config=None) -> list[np.ndarray]:
    """A spinning-coin cycle: full face -> narrowing -> edge-on sliver -> narrowing.
    Built by squeezing the static coin horizontally (palette-safe), so frame 0 is
    the static coin exactly."""
    base = pickup(contract, {**(config or {}), "shape": "coin"})
    return [squeeze_h(base, f) for f in (1.0, 0.55, 0.22, 0.55)]


def pickup_frames(contract, config=None) -> list[np.ndarray] | None:
    """Only the coin spins; other pickups are static."""
    if (config or {}).get("shape", "coin") == "coin":
        return coin_spin(contract, config)
    return None


# ------------------------------- chest ------------------------------------
# `build` swaps the body + band materials; `open` toggles the lid. wood/metal in
# config still override the preset.
_CHEST_BUILDS = {
    "wood":    {"wood": (146, 96, 52),   "metal": (204, 172, 82)},
    "iron":    {"wood": (108, 114, 126), "metal": (176, 182, 194)},
    "gold":    {"wood": (200, 158, 66),  "metal": (242, 218, 122)},
    "crystal": {"wood": (120, 96, 156),  "metal": (190, 216, 238)},
}


def chest(contract, config=None) -> np.ndarray:
    cfg = {"build": "wood", "open": False}
    cfg.update(config or {})
    mat = _CHEST_BUILDS.get(cfg["build"], _CHEST_BUILDS["wood"])
    wood = Ramp(cfg.get("wood", mat["wood"]))
    metal = Ramp(cfg.get("metal", mat["metal"]))
    dark = outline_dark(cfg.get("wood", mat["wood"]))
    cv = _icon(contract)
    cv.rect(8, 14, 3, 12, wood.base)                        # box body
    cv.rect(8, 14, 12, 12, wood.shadow); cv.rect(8, 9, 4, 6, wood.highlight)
    if cfg["open"]:
        cv.rect(3, 5, 3, 12, wood.shadow)                   # lifted lid (behind)
        cv.rect(6, 7, 4, 11, (255, 236, 150)); cv.px(6, 5, (255, 255, 210))   # gold inside
    else:
        cv.rect(5, 7, 3, 12, wood.base); cv.rect(4, 4, 4, 11, wood.base)      # domed lid
        cv.rect(5, 5, 4, 7, wood.highlight); cv.rect(7, 7, 3, 12, wood.shadow)
    for bc in (4, 11):                                       # metal bands
        cv.rect(4, 14, bc, bc, metal.base)
    cv.rect(9, 11, 7, 8, metal.base); cv.px(9, 7, metal.highlight)   # lock
    cv.px(11, 7, dark)                                       # keyhole
    cv.outline(dark)
    return cv.array()


# ----------------------------- projectile ---------------------------------
def _pj_arrow(cv, color):
    wood, metal = Ramp((150, 110, 62)), Ramp(_STEEL)
    for i in range(8):                                       # shaft, low-left -> high-right
        r, c = 12 - i, 3 + i
        cv.px(r, c, wood.base); cv.px(r + 1, c, wood.shadow)
    cv.rect(2, 4, 11, 13, metal.base); cv.px(2, 11, metal.highlight); cv.px(4, 13, metal.shadow)  # head
    cv.rect(11, 13, 2, 4, Ramp(color).base)                 # fletching
    cv.px(13, 2, Ramp(color).shadow)


def _pj_fireball(cv, color):
    fire = Ramp(color)
    cv.disc(8, 9, 4, 4, fire.base); cv.disc(7, 8, 1.8, 1.8, fire.highlight)
    cv.disc(9, 11, 1.8, 1.8, fire.shadow)
    cv.px(6, 7, (255, 255, 210))                            # hot core
    cv.px(12, 4, fire.base); cv.px(13, 3, fire.shadow); cv.px(11, 5, fire.highlight)  # trail


def _pj_bolt(cv, color):
    b = Ramp(color)
    spans = {4: (7, 8), 5: (6, 9), 6: (5, 10), 7: (5, 10), 8: (6, 9), 9: (7, 8)}
    for r, (c0, c1) in spans.items():
        cv.rect(r, r, c0, c1, b.base)
    cv.rect(4, 6, 6, 7, b.highlight)
    cv.px(2, 7, b.base); cv.px(11, 8, b.base); cv.px(7, 3, b.base); cv.px(7, 12, b.base)  # points
    cv.px(4, 7, (255, 255, 255))


def _pj_knife(cv, color):
    blade, grip = Ramp(_STEEL), Ramp((110, 74, 48))
    for i in range(7):                                       # blade: low-left -> high-right
        r, c = 11 - i, 4 + i
        cv.px(r, c, blade.base); cv.px(r + 1, c, blade.shadow); cv.px(r, c + 1, blade.highlight)
    cv.px(4, 11, blade.highlight)                            # tip
    cv.rect(11, 13, 2, 4, grip.base); cv.px(13, 2, grip.shadow)   # handle (low-left)
    cv.px(10, 4, Ramp(color).base)                           # guard fleck


def _pj_shuriken(cv, color):
    st = Ramp(_STEEL)
    cv.rect(3, 13, 8, 8, st.base)                            # vertical blade
    cv.rect(8, 8, 3, 13, st.base)                            # horizontal blade
    cv.disc(8, 8, 2, 2, st.base)                             # hub
    cv.px(6, 6, st.highlight); cv.px(10, 10, st.shadow)      # form light/shade
    cv.px(3, 8, st.highlight); cv.px(8, 13, st.shadow)       # sharpened tips
    cv.px(8, 8, outline_dark(_STEEL))                        # centre hole


_PROJECTILES = {"arrow": _pj_arrow, "fireball": _pj_fireball, "bolt": _pj_bolt,
                "knife": _pj_knife, "shuriken": _pj_shuriken}


def projectile(contract, config=None) -> np.ndarray:
    cfg = {"kind": "arrow", "color": (232, 120, 44)}
    cfg.update(config or {})
    cv = _icon(contract)
    _PROJECTILES.get(cfg["kind"], _pj_arrow)(cv, cfg["color"])
    cv.outline(outline_dark(cfg["color"] if cfg["kind"] != "arrow" else (80, 80, 90)))
    return cv.array()
