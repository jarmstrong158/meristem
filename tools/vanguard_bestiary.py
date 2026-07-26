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


# The six party members, built from the Appearance section of their own character docs
# (vanguard/docs/characters/*.md) rather than invented. Each detail below is something
# the doc actually says; the prop layers (dec-0033) carry the ones that change the
# SILHOUETTE, which is what tells a party apart at 32x32.
#
# These replace third-party Puny-Characters placeholders -- Kael was "Warrior-Blue",
# Lida was "Mage-Cyan" -- with art the project owns and can recolour.
PARTY = {
    # "Warm brown skin, dark hair kept short and practical... field medic's kit --
    #  leather satchel across his chest... Carries his quarterstaff across his back."
    "maren": ("humanoid", {
        "skin": (198, 146, 104), "hair": (54, 44, 38), "hair_style": "short",
        "shirt": (98, 116, 86), "pants": (96, 78, 58),       # muted greens and browns
        "garment": "scarf", "garment_color": (122, 86, 54),  # the satchel strap
        "held": "staff", "held_color": (168, 142, 102),      # his father's ash staff
    }),
    # "Light skin weathered from campaign marches... sandy blond hair cropped
    #  military-short... battered Ashguard-issue armor."
    # Sprite note: "shield always slightly forward" -- so the shield is his silhouette.
    # No helmet: the doc describes his hair, which you could not see under one.
    "kael": ("humanoid", {
        "skin": (222, 182, 146), "hair": (198, 166, 102), "hair_style": "short",
        "shirt": (132, 140, 152), "pants": (96, 102, 114),   # good steel, badly used
        "held": "shield", "held_color": (150, 156, 168),
    }),
    # "Deep brown skin, thick black hair usually pulled back in a messy braid with
    #  dried flowers and herb sprigs tucked into it... An apron with dozens of
    #  pockets... She refuses to give up the apron even in combat."
    "lida": ("humanoid", {
        "skin": (150, 106, 74), "hair": (38, 32, 30), "hair_style": "ponytail",
        "hair_accent": "flora",                              # the tucked sprigs
        "shirt": (110, 124, 88), "pants": (104, 86, 64),     # earthy linen and wool
        "garment": "apron", "garment_color": (214, 202, 172),
        "held": "rod", "held_color": (156, 122, 82),         # the notched rod
    }),
    # "Dark brown skin with warm undertones, tight-coiled black hair worn short (long
    #  hair is a liability)... dark leather vest, loose linen pants... A red scarf
    #  around her neck -- the only colorful thing she owns."
    "senna": ("humanoid", {
        "skin": (142, 94, 66), "hair": (36, 30, 30), "hair_style": "short",
        "shirt": (72, 56, 50), "pants": (150, 140, 124),
        "garment": "scarf", "garment_color": (176, 52, 52),  # her grandmother's
        "held": "flamestaff", "held_color": (60, 50, 48),
    }),
    # "Pale grey-brown skin (common among Hollowfolk)... Black hair, messy, falls into
    #  his eyes... a cloak that seems to eat light... His daggers are strapped to his
    #  thighs."
    # `spiky` for "messy, falls into his eyes" rather than `long`: long hair is the same
    # smooth curve as the cloak below it, so his silhouette came out a featureless mass
    # and his black hair merged into the black cloak. The cloak is also lifted off pure
    # shadow -- it should be the darkest thing in the party, not invisible at 1x.
    "davan": ("humanoid", {
        "skin": (186, 168, 156), "hair": (40, 36, 44), "hair_style": "spiky",
        "shirt": (66, 62, 74), "pants": (52, 48, 58),        # nothing matches
        "garment": "cloak", "garment_color": (58, 54, 76),
        "held": "daggers", "held_color": (162, 168, 180),
    }),
    # "Rich brown skin with a faint grey undertone... a single thick braid... forearms
    #  and knuckles have a permanent grey-stone texture... a Shapers' Guild training
    #  gi... No shoes."
    "yara": ("humanoid", {
        "skin": (140, 104, 82), "hair": (34, 30, 30), "hair_style": "ponytail",
        "shirt": (78, 80, 86), "pants": (64, 66, 72),        # dark grey gi
        "arms": "stone", "arm_color": (132, 136, 142),       # earth-magic reinforcement
        "feet": "bare",                                      # for ground contact
    }),
}

# Vanguard enemy id -> Meristem (archetype, config).
#
# Humanoids here used to be held to <=5 materials for a 15-colour budget. That budget
# is gone (dec-0032: the gate stopped capping colours entirely), so a prop layer no
# longer has to be traded against a palette slot.
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
    # Each of these used to be a shirt colour plus exactly ONE prop, which made twenty
    # of the forty-three read as the same brown figure -- four Archon Sevrins in a row
    # were four purple wizards. With the colour budget gone they can carry a full
    # identity: faction palette (Valcrest fire-reds and steel, Frosthollow ice, Stone-
    # mantle earth) plus a hat AND a held item, so RANK is legible in the silhouette.
    "thornwall_militia":  ("humanoid", {"skin": (214, 172, 132), "hair": (108, 78, 48),
                                        "shirt": (84, 120, 171), "pants": (78, 72, 84),
                                        "held": "shield", "held_color": (150, 150, 160)}),
    # --- the Ashen March: Valcrest's army. Steel over fire-red, rank shown by silhouette.
    "ashguard_soldier":   ("humanoid", {"skin": (222, 178, 140), "hair": (96, 66, 44),
                                        "shirt": (150, 60, 60), "pants": (88, 78, 82),
                                        "hat": "helmet", "hat_color": (176, 182, 194),
                                        "held": "sword", "held_color": (168, 174, 186)}),
    "ashguard_scout":     ("humanoid", {"skin": (216, 170, 130), "hair": (72, 52, 40),
                                        "shirt": (171, 90, 90), "pants": (82, 70, 62),
                                        "hat": "cap", "hat_color": (110, 70, 60),
                                        "held": "daggers", "held_color": (160, 166, 178)}),
    "ashguard_mage":      ("humanoid", {"skin": (226, 182, 142), "hair": (58, 44, 40),
                                        "shirt": (135, 40, 40), "pants": (74, 52, 52),
                                        "hat": "hood", "hat_color": (104, 32, 32),
                                        "held": "flamestaff", "held_color": (150, 120, 84)}),
    "ashguard_officer":   ("humanoid", {"skin": (228, 186, 148), "hair": (188, 156, 100),
                                        "shirt": (200, 69, 69), "pants": (92, 62, 62),
                                        "hat": "crown", "hat_color": (230, 200, 110),
                                        "garment": "cloak", "garment_color": (128, 36, 36),
                                        "held": "sword", "held_color": (198, 204, 216)}),
    "ashguard_veteran":   ("humanoid", {"skin": (206, 160, 122), "hair": (150, 146, 140),
                                        "shirt": (150, 55, 55), "pants": (80, 72, 76),
                                        "hat": "helmet", "hat_color": (140, 120, 120),
                                        "held": "shield", "held_color": (146, 138, 132)}),
    # anti-Conduit specialist: hooded, carries a suppression rod rather than a blade
    "ashguard_suppressor": ("humanoid", {"skin": (212, 166, 128), "hair": (52, 40, 38),
                                         "shirt": (140, 45, 45), "pants": (70, 58, 60),
                                         "hat": "hood", "hat_color": (90, 40, 40),
                                         "held": "rod", "held_color": (128, 100, 108)}),
    "crystallized_mage":  ("humanoid", {"skin": (216, 224, 236), "hair": (176, 206, 226),
                                        "shirt": (150, 180, 220), "pants": (110, 140, 178),
                                        "hat": "wizard", "hat_color": (120, 170, 210),
                                        "arms": "stone", "arm_color": (192, 214, 232)}),
    "captain_rhogar":     ("humanoid", {"skin": (206, 156, 118), "hair": (78, 54, 40),
                                        "beard": "full", "shirt": (204, 90, 51),
                                        "pants": (86, 66, 56), "hat": "helmet",
                                        "hat_color": (150, 60, 40),
                                        "garment": "cloak", "garment_color": (140, 58, 34),
                                        "held": "greatsword", "held_color": (196, 202, 214)}),
    "emberlord_vasek":    ("humanoid", {"skin": (222, 174, 132), "hair": (198, 122, 44),
                                        "beard": "short", "shirt": (230, 96, 20),
                                        "pants": (104, 56, 24), "hat": "crown",
                                        "hat_color": (255, 160, 40),
                                        "garment": "cloak", "garment_color": (186, 74, 18),
                                        "held": "flamestaff", "held_color": (120, 62, 30)}),
    "commander_haric":    ("humanoid", {"skin": (198, 150, 116), "hair": (60, 48, 44),
                                        "beard": "short", "shirt": (153, 60, 33),
                                        "pants": (78, 60, 52), "hat": "helmet",
                                        "hat_color": (110, 50, 30),
                                        "held": "axe", "held_color": (176, 182, 194)}),
    # --- Archon Sevrin, four phases. An Absorber Conduit and Maren's mirror, so each
    # phase escalates the SILHOUETTE (hooded stranger -> revealed -> empowered ->
    # ascendant) instead of four near-identical purple wizards.
    "archon_sevrin_first": ("humanoid", {"skin": (206, 186, 196), "hair": (40, 32, 52),
                                         "shirt": (60, 30, 150), "pants": (44, 28, 72),
                                         "hat": "hood", "hat_color": (50, 24, 120)}),
    "archon_sevrin_p1":   ("humanoid", {"skin": (208, 188, 200), "hair": (44, 34, 60),
                                        "shirt": (85, 40, 190), "pants": (52, 30, 96),
                                        "hat": "hood", "hat_color": (70, 33, 160),
                                        "held": "staff", "held_color": (126, 96, 186)}),
    "archon_sevrin_p2":   ("humanoid", {"skin": (212, 194, 208), "hair": (168, 150, 200),
                                        "shirt": (100, 45, 205), "pants": (60, 34, 120),
                                        "hat": "wizard", "hat_color": (85, 33, 204),
                                        "garment": "cloak", "garment_color": (74, 36, 150),
                                        "held": "staff", "held_color": (170, 140, 230)}),
    "archon_sevrin_p3":   ("humanoid", {"skin": (226, 212, 228), "hair": (214, 196, 246),
                                        "shirt": (130, 60, 235), "pants": (78, 44, 156),
                                        "hat": "crown", "hat_color": (196, 150, 255),
                                        "garment": "cloak", "garment_color": (108, 52, 206),
                                        "held": "flamestaff", "held_color": (196, 160, 250)}),
    # a reflection of Maren: the same staff and satchel strap, drained of colour
    "the_mirror":         ("humanoid", {"skin": (198, 202, 212), "hair": (150, 156, 170),
                                        "shirt": (171, 186, 204), "pants": (136, 146, 164),
                                        "garment": "scarf", "garment_color": (150, 160, 178),
                                        "held": "staff", "held_color": (176, 186, 200)}),
    "stillkeeper_acolyte": ("humanoid", {"skin": (230, 214, 210), "hair": (204, 218, 230),
                                         "shirt": (69, 170, 210), "pants": (58, 108, 148),
                                         "hat": "hood", "hat_color": (58, 142, 184),
                                         "held": "rod", "held_color": (170, 210, 230)}),
    # Stonemantle Shapers' Guild: bald, stone-reinforced, barefoot for ground contact
    "yara_ironvein":      ("humanoid", {"skin": (150, 112, 88), "hair_style": "bald",
                                        "shirt": (150, 120, 70), "pants": (96, 80, 56),
                                        "arms": "stone", "arm_color": (150, 140, 120),
                                        "feet": "bare"}),
    "granite_golem":      ("humanoid", {"skin": (146, 146, 156), "hair_style": "bald",
                                        "shirt": (120, 120, 130), "pants": (98, 98, 110),
                                        "arms": "stone", "arm_color": (168, 168, 180),
                                        "feet": "bare"}),
    "lattice_sentinel":   ("humanoid", {"skin": (206, 220, 238), "hair_style": "bald",
                                        "shirt": (150, 170, 210), "pants": (110, 132, 176),
                                        "hat": "helmet", "hat_color": (180, 200, 230),
                                        "arms": "stone", "arm_color": (188, 206, 232),
                                        "held": "spear", "held_color": (196, 214, 236)}),
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


def _contact_sheet(tiles, title, path, cols=7, cell=64):
    GAP, LH, M = 6, 22, 12
    rows = (len(tiles) + cols - 1) // cols
    W = M * 2 + cols * (cell + GAP)
    H = M * 2 + rows * (cell + LH + GAP) + 20
    cs = Image.new("RGBA", (W, H), (34, 37, 44, 255))
    d = ImageDraw.Draw(cs)
    F = ImageFont.load_default()
    d.text((M, M), title, fill=(232, 236, 244), font=F)
    y0 = M + 20
    for i, (name, arch, idle, ok) in enumerate(tiles):
        x = M + (i % cols) * (cell + GAP)
        y = y0 + (i // cols) * (cell + LH + GAP)
        d.rectangle([x, y, x + cell - 1, y + cell - 1],
                    fill=(44, 48, 57, 255) if ok else (70, 40, 40, 255))
        cs.alpha_composite(idle.resize((cell, cell), Image.NEAREST), (x, y))
        d.text((x, y + cell), name[:13], fill=(150, 158, 172), font=F)
        d.text((x, y + cell + 10), arch, fill=(120, 128, 142), font=F)
    cs.save(path)


def _render_group(group: dict, out_dir: Path):
    tiles, fails = [], []
    for name, (arch, cfg) in group.items():
        sheet, idle = build_sheet(arch, cfg)
        res = validate(idle, archetype_class(arch), C)
        if not res.accepted:
            fails.append((name, arch, res.reasons))
        sheet.save(out_dir / f"{name}.png")
        tiles.append((name, arch, idle, res.accepted))
    return tiles, fails


def main(out_dir: Path) -> None:
    enemies_dir = out_dir / "enemies"
    cast_dir = out_dir / "characters"
    enemies_dir.mkdir(parents=True, exist_ok=True)
    cast_dir.mkdir(parents=True, exist_ok=True)

    beasts, beast_fails = _render_group(BESTIARY, enemies_dir)
    cast, cast_fails = _render_group(PARTY, cast_dir)

    _contact_sheet(beasts,
                   f"Vanguard bestiary via Meristem  ({len(beasts)} creatures, "
                   f"{len(beast_fails)} gate-fails)",
                   ROOT / "docs" / "reference" / "vanguard-bestiary.png")
    _contact_sheet(cast,
                   f"Vanguard party via Meristem  ({len(cast)} characters, "
                   f"{len(cast_fails)} gate-fails) -- built from their own doc appearances",
                   ROOT / "docs" / "reference" / "vanguard-cast.png", cols=6, cell=96)

    print(f"wrote {len(beasts)} creature sheets -> {enemies_dir}")
    print(f"wrote {len(cast)} party sheets     -> {cast_dir}")
    print("contact sheets -> docs/reference/vanguard-bestiary.png, vanguard-cast.png")
    fails = beast_fails + cast_fails
    if fails:
        print("GATE FAILURES:")
        for name, arch, reasons in fails:
            print(f"  {name} ({arch}): {reasons}")
    else:
        print("all idles gate-clean.")


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "build" / "vanguard-sprites"
    main(out)
