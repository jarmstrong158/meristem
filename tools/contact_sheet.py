"""Render a contact sheet of the entire sprite library -> docs/reference/library.png.

A browsable visual index: every archetype and every build/kind, labelled. Purely a
projection of the generators (deterministic), so re-running reproduces it byte-for-byte.

    python tools/contact_sheet.py
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "generators"))
sys.path.insert(0, str(ROOT / "packages" / "asset-gate"))

from asset_gate import load_contract                                     # noqa: E402
from meristem_generators.creatures import (build_blob, build_flyer,       # noqa: E402
                                           build_ghost, build_quadruped,
                                           build_serpent, build_spider)
from meristem_generators.humanoid import build_humanoid                  # noqa: E402
from meristem_generators.items import (chest, consumable, pickup,         # noqa: E402
                                       projectile, weapon)
from meristem_generators.procedural import (ProceduralGenerator,          # noqa: E402
                                            build_tile)

C = load_contract(str(ROOT / "experiments" / "00-bakeoff" / "style-contract.json"))


def im(a):
    return Image.fromarray(a, "RGBA")


def _creatures():
    out = []
    for b, col in [("slime", (96, 200, 96)), ("king", (90, 150, 235)),
                   ("cube", (120, 220, 210)), ("ooze", (170, 120, 210))]:
        out.append((f"blob:{b}", im(build_blob(C, {"build": b, "color": col}))))
    for b, col in [("ghost", (224, 228, 244)), ("wisp", (120, 210, 240)), ("specter", (150, 150, 180))]:
        out.append((f"ghost:{b}", im(build_ghost(C, {"build": b, "color": col}))))
    for b in ("dog", "wolf", "boar", "cat"):
        out.append((f"quad:{b}", im(build_quadruped(C, {"build": b}))))
    for b, col in [("bat", (92, 80, 112)), ("bird", (150, 90, 70)), ("moth", (180, 170, 120))]:
        out.append((f"flyer:{b}", im(build_flyer(C, {"build": b, "color": col}))))
    for b, col in [("cobra", (86, 158, 92)), ("snake", (150, 140, 70)), ("viper", (150, 90, 80))]:
        out.append((f"serpent:{b}", im(build_serpent(C, {"build": b, "color": col}))))
    for b, col in [("spider", (74, 66, 82)), ("tarantula", (96, 70, 54)), ("widow", (40, 40, 48))]:
        out.append((f"spider:{b}", im(build_spider(C, {"build": b, "color": col}))))
    return out


def _characters():
    combos = [
        ("plain", {}),
        ("knight", {"hat": "helmet", "hat_color": (176, 182, 194), "shirt": (120, 126, 140)}),
        ("wizard", {"hat": "wizard", "hat_color": (70, 60, 140), "beard": "full",
                    "hair": (220, 220, 225), "shirt": (90, 70, 150)}),
        ("king", {"hat": "crown", "hat_color": (242, 214, 120), "beard": "full",
                  "hair": (120, 90, 60), "shirt": (150, 40, 60)}),
        ("dwarf", {"beard": "full", "hair": (170, 90, 50), "shirt": (120, 80, 50)}),
        ("rogue", {"hat": "cap", "hat_color": (90, 70, 60), "hair_style": "ponytail", "shirt": (70, 90, 70)}),
        ("cleric", {"beard": "short", "hair_style": "bald", "shirt": (210, 200, 180)}),
        # prop/accessory layers — distinctness by silhouette, not palette
        ("staff", {"held": "staff", "held_color": (150, 120, 84), "shirt": (86, 108, 70)}),
        ("shield", {"hat": "helmet", "hat_color": (176, 182, 194), "shirt": (120, 126, 140),
                    "held": "shield", "held_color": (150, 156, 168)}),
        ("apron+rod", {"garment": "apron", "garment_color": (214, 202, 172), "hair_accent": "flora",
                       "hair_style": "ponytail", "held": "rod", "held_color": (156, 122, 82)}),
        ("scarf+flame", {"garment": "scarf", "garment_color": (176, 52, 52),
                         "held": "flamestaff", "held_color": (60, 50, 48), "shirt": (66, 52, 46)}),
        ("hood+daggers", {"hat": "hood", "hat_color": (52, 50, 58), "shirt": (56, 54, 62),
                          "held": "daggers", "held_color": (150, 156, 168)}),
        ("barefoot+stone", {"feet": "bare", "arms": "stone", "hair_style": "long",
                            "shirt": (86, 90, 98), "skin": (150, 112, 84)}),
    ]
    return [(nm, im(build_humanoid(C, cfg))) for nm, cfg in combos]


def _list(fn, key, kinds):
    return [(k, im(fn(C, {key: k}))) for k in kinds]


def _chests():
    out = [(b, im(chest(C, {"build": b}))) for b in ("wood", "iron", "gold", "crystal")]
    out.append(("gold:open", im(chest(C, {"build": "gold", "open": True}))))
    return out


def _tiles():
    names = ("grass", "dirt", "water", "stone", "sand", "snow", "lava", "brick")
    return [(n, im(build_tile(C, n, **ProceduralGenerator._TILES[n]))) for n in names]


def build_sections():
    """Every archetype × build, grouped and labelled. Pure (deterministic)."""
    return [
        ("Creatures  (archetype:build)", _creatures()),
        ("Characters  (humanoid layers)", _characters()),
        ("Weapons", _list(weapon, "kind", ["sword", "dagger", "greatsword", "axe", "spear", "staff", "bow", "mace", "wand"])),
        ("Consumables", _list(consumable, "shape", ["flask", "bottle", "vial", "scroll", "pouch"])),
        ("Pickups", _list(pickup, "shape", ["coin", "heart", "key", "gem", "ring", "skull", "star"])),
        ("Projectiles", _list(projectile, "kind", ["arrow", "fireball", "bolt", "knife", "shuriken"])),
        ("Chests", _chests()),
        ("Tiles", _tiles()),
    ]


# ---- layout ----
CELL = 84
GAP = 8
LABEL_H = 12
HEADER_H = 24
COLS = 9
MARGIN = 14
BG = (34, 37, 44, 255)
HEADER = (232, 236, 244)
LABEL = (150, 158, 172)
CELLBG = (44, 48, 57, 255)
FONT = ImageFont.load_default()


def _rows(n):
    return (n + COLS - 1) // COLS


def render(out_path: Path) -> tuple[int, int, int]:
    sections = build_sections()
    total_h = MARGIN
    for _, entries in sections:
        total_h += HEADER_H + _rows(len(entries)) * (CELL + LABEL_H + GAP)
    total_h += MARGIN
    total_w = MARGIN * 2 + COLS * CELL + (COLS - 1) * GAP

    sheet = Image.new("RGBA", (total_w, total_h), BG)
    draw = ImageDraw.Draw(sheet)

    y = MARGIN
    for title, entries in sections:
        draw.text((MARGIN, y + 6), title, fill=HEADER, font=FONT)
        y += HEADER_H
        for i, (label, sprite) in enumerate(entries):
            x = MARGIN + (i % COLS) * (CELL + GAP)
            cy = y + (i // COLS) * (CELL + LABEL_H + GAP)
            draw.rectangle([x, cy, x + CELL - 1, cy + CELL - 1], fill=CELLBG)
            scale = CELL // sprite.width
            big = sprite.resize((sprite.width * scale, sprite.height * scale), Image.NEAREST)
            sheet.alpha_composite(big, (x + (CELL - big.width) // 2, cy + (CELL - big.height) // 2))
            draw.text((x + 2, cy + CELL), label, fill=LABEL, font=FONT)
        y += _rows(len(entries)) * (CELL + LABEL_H + GAP)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.convert("RGBA").save(out_path)
    return total_w, total_h, sum(len(e) for _, e in sections)


if __name__ == "__main__":
    out = ROOT / "docs" / "reference" / "library.png"
    w, h, n = render(out)
    print(f"wrote {out}  ({w}x{h}, {n} sprites)")
