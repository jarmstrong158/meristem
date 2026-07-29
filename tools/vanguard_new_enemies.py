"""Generate battle sheets for Vanguard enemies that have no sprite yet.

tools/vanguard_bestiary.py carries a hand-authored (archetype, config) per enemy, which
was right for 43 creatures picked one at a time. Fifty more arrived at once when the
design doc's roster was finally built, and hand-mapping those would be fifty judgement
calls about colour where the enemy already states its own family and element.

So this DERIVES the mapping: family picks the Meristem archetype, element picks the
palette, level nudges the value so a late-game creature reads heavier than an early one.
Anything already in BESTIARY is left alone -- a hand-picked sprite beats a derived one.

    python tools/vanguard_new_enemies.py <vanguard_repo> [out_dir]
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "generators"))
sys.path.insert(0, str(ROOT / "packages" / "asset-gate"))
sys.path.insert(0, str(ROOT / "tools"))

from asset_gate import validate                                  # noqa: E402
from vanguard_bestiary import BESTIARY, C, build_sheet, _contact_sheet   # noqa: E402

# Vanguard's `family` -> Meristem archetype + the build within it.
FAMILY = {
    "wolf":      ("quadruped", "wolf"),
    "serpent":   ("serpent", "viper"),
    "raptor":    ("flyer", "bird"),
    "slime":     ("blob", "slime"),
    "beetle":    ("beetle", "beetle"),
    "wisp":      ("ghost", "wisp"),
    "construct": ("humanoid", None),
    "plant":     ("serpent", "viper"),      # vines read as a coiled length, not a person
    "beast":     ("quadruped", "wolf"),
    "humanoid":  ("humanoid", None),
}

# element -> base colour. Neutral creatures take their region's earth tones.
ELEMENT = {
    "fire":      (206, 92, 52),
    "ice":       (140, 196, 224),
    "dark":      (96, 78, 128),
    "earth":     (140, 116, 82),
    "light":     (232, 214, 150),
    "lightning": (226, 200, 88),
    "water":     (84, 140, 178),
    "wind":      (150, 196, 158),
    "":          (132, 128, 116),
}


# ai_type -> the prop layer that makes the role readable at 32x32. `None` is filled in
# with the creature's own colour (hat) or steel (weapon) by config_for.
ROLE_KIT = {
    "caster":   {"held": "staff", "held_color": None, "hat": "wizard", "hat_color": None},
    "tank":     {"hat": "helmet", "hat_color": None, "held": "shield", "held_color": None},
    "brute":    {"held": "sword", "held_color": None},
    "assassin": {"held": "daggers", "held_color": None, "hat": "hood", "hat_color": None},
    "swarm":    {"held": "dagger", "held_color": None},
    "support":  {"held": "rod", "held_color": None, "garment": "cloak",
                 "garment_color": None},
}


def read_enemies(vg: Path) -> list[dict]:
    out = []
    for f in sorted((vg / "data" / "enemies").glob("*.tres")):
        t = f.read_text(encoding="utf-8")
        def g(k, d=""):
            m = re.search(rf'^{k} = "?([^"\n]*)"?$', t, re.M)
            return m.group(1).strip() if m else d
        out.append({"id": g("id"), "name": g("display_name"), "family": g("family"),
                    "element": g("element"), "level": int(g("level", "1") or 1),
                    "ai": g("ai_type", "brute"), "boss": "is_boss = true" in t})
    return out


def config_for(e: dict) -> tuple[str, dict]:
    arch, build = FAMILY.get(e["family"], ("humanoid", None))
    r, g, b = ELEMENT.get(e["element"], ELEMENT[""])
    # a level-27 creature should not be the same brightness as a level-2 one: darken
    # toward the deep end so the Lattice Core reads heavier than Thornwall
    k = max(0.62, 1.0 - e["level"] * 0.012)
    col = (int(r * k), int(g * k), int(b * k))

    if arch == "humanoid":
        skin = col if e["family"] == "construct" else (198, 160, 124)
        cfg = {"skin": skin, "hair": (58, 48, 44), "shirt": col,
               "pants": (int(col[0] * 0.6), int(col[1] * 0.6), int(col[2] * 0.6))}
        # Thirteen Ashguard variants share a family and an element, so colour alone
        # made them one orange person thirteen times. Their ROLE is already in the
        # data, and role is what changes a silhouette: a caster holds a staff, a tank
        # wears a helmet and carries a shield, an assassin has knives.
        steel = (188, 194, 208)
        cfg |= ROLE_KIT.get(e["ai"], {})
        for key in ("hat_color", "held_color", "garment_color"):
            if key in cfg and cfg[key] is None:
                cfg[key] = steel if key == "held_color" else col
        if e["boss"]:
            cfg |= {"hat": "crown", "hat_color": (214, 176, 72)}
        return arch, cfg
    cfg = {"color": col}
    if build:
        cfg["build"] = build
    if arch == "blob" and e["boss"]:
        cfg["size"] = "l"
    return arch, cfg


def main(vg: Path, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    enemies = read_enemies(vg)
    new = [e for e in enemies if e["id"] and e["id"] not in BESTIARY]
    print(f"{len(enemies)} enemies, {len(enemies) - len(new)} already mapped, {len(new)} to build")

    tiles, fails = [], []
    for e in new:
        arch, cfg = config_for(e)
        sheet, idle = build_sheet(arch, cfg)
        res = validate(idle, "enemy", C)
        if not res.accepted:
            fails.append((e["id"], res.reasons))
        sheet.save(out_dir / f"{e['id']}.png")
        tiles.append((e["id"], arch, idle, res.accepted))

    _contact_sheet(tiles, f"Vanguard: {len(tiles)} newly built enemies, sprites derived "
                          f"from family + element",
                   ROOT / "docs" / "reference" / "vanguard-new-enemies.png", cols=8, cell=64)
    print(f"wrote {len(tiles)} sheets -> {out_dir}")
    print("all gate-clean." if not fails else f"GATE FAILURES: {fails}")

    # the SPRITE_MAP lines Vanguard needs, so the battle loader can find them
    lines = "\n".join(f'\t"{e["id"]}": "res://sprites/enemies/{e["id"]}.png",' for e in new)
    (out_dir / "sprite_map_additions.txt").write_text(lines, encoding="utf-8")
    print(f"SPRITE_MAP additions -> {out_dir / 'sprite_map_additions.txt'}")


if __name__ == "__main__":
    vg = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r"C:\Users\jarms\repos\vanguard")
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "build" / "vanguard-new-enemies"
    main(vg, out)
