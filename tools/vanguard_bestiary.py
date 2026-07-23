"""Generate Vanguard's full 43-creature bestiary as Meristem sprites, packed into the
Puny-layout battle sheets the Vanguard `battle_sprite_loader` consumes.

Each Vanguard enemy id is mapped to a Meristem `(archetype, config)` (dec-0022) — the
families line up (wolf->quadruped, slime->blob, wisp->ghost, raptor/beetle now exist),
recoloured from each enemy's base_color / element. Every sprite is hue-shifted + gated —
an upgrade over Vanguard's grey-default-slime placeholders (20 of 43 today).

Output per id: a 768x256 sheet (24 cols x 8 rows of 32x32). Only row 0 (south/front) is
filled — the loader reads it and flips_h, so art is drawn facing RIGHT. Col 0 = idle;
the idle-anim cycle fills the walk cols (0-5); all other cols default to idle so no
animation samples an empty cell.

    python tools/vanguard_bestiary.py [out_dir]     # default: build/vanguard-bestiary
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "generators"))
sys.path.insert(0, str(ROOT / "packages" / "asset-gate"))

from asset_gate import load_contract, validate                       # noqa: E402
from meristem_generators import (archetype_class, archetype_frames,   # noqa: E402
                                 build_archetype)

C = load_contract(str(ROOT / "experiments" / "00-bakeoff" / "style-contract.json"))


def _h(archetype, **cfg):
    return (archetype, cfg)


# Vanguard enemy id -> Meristem (archetype, config). Humanoids keep to <=5 materials
# (base skin/hair/shirt/pants + ONE extra layer) to hold the 15-colour budget.
BESTIARY = {
    # --- wolves (quadruped) ---
    "thornwall_wolf":   ("quadruped", {"build": "wolf", "color": (140, 115, 84)}),
    "cinder_wolf":      ("quadruped", {"build": "wolf", "color": (204, 102, 51)}),
    "frost_wolf":       ("quadruped", {"build": "wolf", "color": (150, 182, 212)}),
    "pyrebeast_alpha":  ("quadruped", {"build": "boar", "color": (171, 33, 33)}),   # boss: heavier build
    "lattice_hound":    ("quadruped", {"build": "wolf", "color": (120, 96, 168)}),
    # --- slimes (blob) ---
    "marsh_slime":      ("blob", {"build": "slime", "color": (69, 186, 69)}),
    "brine_ooze":       ("blob", {"build": "ooze", "color": (92, 156, 162)}),
    "storm_jelly":      ("blob", {"build": "slime", "color": (120, 140, 232)}),
    "deep_angler":      ("blob", {"build": "ooze", "color": (46, 66, 96)}),          # deep-sea beast (approx)
    # --- serpents ---
    "firepit_adder":    ("serpent", {"build": "viper", "color": (200, 100, 60)}),
    "ironscale_lizard": ("serpent", {"build": "snake", "color": (112, 124, 112)}),
    "hollow_vine":      ("serpent", {"build": "snake", "color": (64, 96, 60)}),      # plant/vine (approx)
    # --- beetles/bugs ---
    "ember_scorpion":   ("beetle", {"build": "scorpion", "color": (171, 84, 51)}),
    "ice_scarab":       ("beetle", {"build": "beetle", "color": (150, 190, 212)}),
    "shadow_creeper":   ("spider", {"build": "spider", "color": (48, 42, 58)}),      # dark crawler (approx)
    # --- flyers ---
    "savannah_hawk":    ("flyer", {"build": "bird", "color": (102, 135, 171)}),
    "cave_bat_colony":  ("flyer", {"build": "bat", "color": (92, 82, 112)}),
    "gloom_moth":       ("flyer", {"build": "moth", "color": (96, 84, 116)}),
    # --- wisps / wraiths (ghost) ---
    "flame_sprite":     ("ghost", {"build": "wisp", "color": (255, 135, 51)}),
    "flameling":        ("ghost", {"build": "wisp", "color": (204, 102, 33)}),
    "frost_wraith":     ("ghost", {"build": "specter", "color": (150, 190, 220)}),
    "hollow_stalker":   ("ghost", {"build": "specter", "color": (58, 40, 78)}),
    "lattice_stalker":  ("ghost", {"build": "specter", "color": (96, 72, 144)}),
    # --- raptors ---
    # (savannah_hawk is a bird -> flyer above; the raptor archetype covers scaly beasts)
    # --- humanoids: militia / ashguard / mages / bosses / specials ---
    "thornwall_militia":  ("humanoid", {"shirt": (84, 120, 171), "held": "shield", "held_color": (150, 150, 160)}),
    "ashguard_soldier":   ("humanoid", {"shirt": (150, 60, 60), "hat": "helmet", "hat_color": (176, 182, 194)}),
    "ashguard_scout":     ("humanoid", {"shirt": (171, 90, 90), "hat": "cap", "hat_color": (110, 70, 60)}),
    "ashguard_mage":      ("humanoid", {"shirt": (135, 40, 40), "held": "flamestaff", "held_color": (150, 120, 84)}),
    "ashguard_officer":   ("humanoid", {"shirt": (200, 69, 69), "hat": "crown", "hat_color": (230, 200, 110)}),
    "ashguard_veteran":   ("humanoid", {"shirt": (150, 55, 55), "hat": "helmet", "hat_color": (140, 120, 120)}),
    "ashguard_suppressor": ("humanoid", {"shirt": (140, 45, 45), "hat": "hood", "hat_color": (90, 40, 40)}),
    "crystallized_mage":  ("humanoid", {"shirt": (150, 180, 220), "hat": "wizard", "hat_color": (120, 170, 210)}),
    "captain_rhogar":     ("humanoid", {"shirt": (204, 90, 51), "hat": "helmet", "hat_color": (150, 60, 40)}),
    "emberlord_vasek":    ("humanoid", {"shirt": (230, 96, 20), "hat": "crown", "hat_color": (255, 160, 40)}),
    "commander_haric":    ("humanoid", {"shirt": (153, 60, 33), "hat": "helmet", "hat_color": (110, 50, 30)}),
    "archon_sevrin_first": ("humanoid", {"shirt": (60, 30, 150), "hat": "hood", "hat_color": (50, 24, 120)}),
    "archon_sevrin_p1":   ("humanoid", {"shirt": (85, 40, 190), "hat": "wizard", "hat_color": (70, 33, 160)}),
    "archon_sevrin_p2":   ("humanoid", {"shirt": (100, 45, 205), "hat": "wizard", "hat_color": (85, 33, 204)}),
    "archon_sevrin_p3":   ("humanoid", {"shirt": (130, 60, 235), "hat": "wizard", "hat_color": (150, 90, 245)}),
    "the_mirror":         ("humanoid", {"shirt": (171, 186, 204), "hat": "hood", "hat_color": (150, 165, 185)}),
    "stillkeeper_acolyte": ("humanoid", {"shirt": (69, 170, 210), "held": "rod", "held_color": (170, 210, 230)}),
    "yara_ironvein":      ("humanoid", {"shirt": (150, 120, 70), "hair_style": "bald", "arms": "stone", "arm_color": (150, 140, 120)}),
    "granite_golem":      ("humanoid", {"shirt": (120, 120, 130), "arms": "stone", "arm_color": (140, 140, 150)}),
    "lattice_sentinel":   ("humanoid", {"shirt": (150, 170, 210), "hat": "helmet", "hat_color": (180, 200, 230)}),
}


def build_sheet(archetype, config):
    """A 768x256 Puny sheet: row 0 filled with the idle frame, walk cols carry the
    idle-anim cycle. Returns (sheet, idle_frame)."""
    frames = archetype_frames(C, archetype, config)
    idle = frames[0] if frames else build_archetype(C, archetype, config)
    frames = frames or [idle]
    sheet = Image.new("RGBA", (768, 256), (0, 0, 0, 0))
    for col in range(24):                                    # every col = idle (no empty samples)
        sheet.paste(idle, (col * 32, 0), idle)
    for col in range(6):                                     # walk cols 0-5 = anim cycle
        f = frames[col % len(frames)]
        sheet.paste(f, (col * 32, 0), f)
    return sheet, idle


def main(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    tiles = []
    fails = []
    for eid, (arch, cfg) in BESTIARY.items():
        sheet, idle = build_sheet(arch, cfg)
        res = validate(idle, archetype_class(arch), C)
        if not res.accepted:
            fails.append((eid, arch, res.reasons))
        sheet.save(out_dir / f"{eid}.png")
        tiles.append((eid, arch, idle, res.accepted))

    # a contact sheet for eyeball review
    CELL, GAP, LH, COLS, M = 64, 6, 22, 7, 12
    rows = (len(tiles) + COLS - 1) // COLS
    W = M * 2 + COLS * (CELL + GAP)
    H = M * 2 + rows * (CELL + LH + GAP) + 20
    cs = Image.new("RGBA", (W, H), (34, 37, 44, 255))
    d = ImageDraw.Draw(cs)
    F = ImageFont.load_default()
    d.text((M, M), f"Vanguard bestiary via Meristem  ({len(tiles)} creatures, {len(fails)} gate-fails)", fill=(232, 236, 244), font=F)
    y0 = M + 20
    for i, (eid, arch, idle, ok) in enumerate(tiles):
        x = M + (i % COLS) * (CELL + GAP)
        y = y0 + (i // COLS) * (CELL + LH + GAP)
        d.rectangle([x, y, x + CELL - 1, y + CELL - 1], fill=(44, 48, 57, 255) if ok else (70, 40, 40, 255))
        big = idle.resize((CELL, CELL), Image.NEAREST)
        cs.alpha_composite(big, (x, y))
        d.text((x, y + CELL), eid[:13], fill=(150, 158, 172), font=F)
        d.text((x, y + CELL + 10), arch, fill=(120, 128, 142), font=F)
    cs.save(ROOT / "docs" / "reference" / "vanguard-bestiary.png")

    print(f"wrote {len(tiles)} sheets to {out_dir}")
    print(f"contact sheet -> docs/reference/vanguard-bestiary.png")
    if fails:
        print("GATE FAILURES:")
        for eid, arch, reasons in fails:
            print(f"  {eid} ({arch}): {reasons}")
    else:
        print("all idles gate-clean.")


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "build" / "vanguard-bestiary"
    main(out)
