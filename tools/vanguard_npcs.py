"""Generate a four-direction overworld sheet for every NPC actually placed in Vanguard,
from that NPC's own resolved palette.

The 18 generic `sprite_id` sheets from tools/vanguard_bestiary.py could not be used in
the overworld: a placed NPC carries hand-authored shirt/pants/hair/skin colours, so a
sheet keyed on sprite_id would have made every "worker_cyan" in the game the same
person. This keys on the NPC instead, so the variety is preserved exactly -- it is
authored, not random, and there are only fifteen of them.

Input is the JSON that Vanguard's tools/dump_npc_palettes.gd writes. That dump reads
the palette off the LIVE node rather than parsing .tscn, because colours the author
left unset are derived at runtime from npc_color plus a hash of the node name --
re-deriving that here would be a second implementation of the same rule, free to drift.

    godot --headless --script res://tools/dump_npc_palettes.gd -- npcs.json   # in vanguard
    python tools/vanguard_npcs.py npcs.json [out_dir]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "generators"))
sys.path.insert(0, str(ROOT / "packages" / "asset-gate"))

from asset_gate import load_contract, validate                      # noqa: E402
from meristem_generators.humanoid import build_humanoid             # noqa: E402

sys.path.insert(0, str(ROOT / "tools"))
from vanguard_bestiary import build_overworld_sheet                 # noqa: E402

C = load_contract(str(ROOT / "experiments" / "00-bakeoff" / "style-contract.json"))

# Vanguard's hat vocabulary -> Meristem's. `wide_brim` and `headband` were added to the
# humanoid for this; the rest already existed. A straw hat is a wide brim in straw.
HATS = {
    "none": "none",
    "cap": "cap",
    "hood": "hood",
    "headband": "headband",
    "wide_brim": "wide_brim",
    "straw_hat": "wide_brim",
}

# Vanguard's npc_controller says female NPCs get long hair and a dress/skirt variant.
# Meristem carries that as a hair style plus a garment, both of which change the
# SILHOUETTE -- which is what tells two villagers apart at 32x32 across a room.
FEMALE_HAIR, MALE_HAIR = "long", "short"


def _rgb(hex_str: str) -> tuple[int, int, int]:
    h = hex_str.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def to_config(npc: dict) -> dict:
    """One placed NPC's resolved palette as a Meristem humanoid config."""
    female = bool(npc.get("is_female"))
    cfg = {
        "skin": _rgb(npc["skin"]),
        "hair": _rgb(npc["hair"]),
        "shirt": _rgb(npc["shirt"]),
        "pants": _rgb(npc["pants"]),
        "hair_style": FEMALE_HAIR if female else MALE_HAIR,
        "hat": HATS.get(npc.get("hat_type", "none"), "none"),
        "hat_color": _rgb(npc["hat"]),
    }
    if female:
        # the skirt reads as a second silhouette, not just a recolour
        cfg["garment"] = "apron"
        cfg["garment_color"] = _rgb(npc["pants"])
    return cfg


def sheet_key(npc: dict) -> str:
    """File stem for one NPC. Keyed on map + node so two NPCs that happen to share a
    display name (there are several "Traveler"s in a JRPG) cannot collide."""
    return f"{npc['map']}_{npc['node']}".lower()


def main(dump_path: Path, out_dir: Path) -> None:
    npcs = json.loads(dump_path.read_text(encoding="utf-8"))
    out_dir.mkdir(parents=True, exist_ok=True)
    written, skipped, fails = [], [], []
    for npc in npcs:
        # a named party member already has a sheet built from their character doc,
        # which is better art than anything derivable from a scene's colour exports
        if npc.get("character_id"):
            skipped.append((npc["npc_name"], npc["character_id"]))
            continue
        cfg = to_config(npc)
        res = validate(Image.fromarray(build_humanoid(C, cfg), "RGBA"), "character", C)
        if not res.accepted:
            fails.append((npc["npc_name"], res.reasons))
        key = sheet_key(npc)
        build_overworld_sheet(cfg).save(out_dir / f"{key}.png")
        written.append((key, npc, cfg))

    _contact_sheet(written, ROOT / "docs" / "reference" / "vanguard-npcs-overworld.png")
    print(f"wrote {len(written)} NPC overworld sheets -> {out_dir}")
    for name, cid in skipped:
        print(f"  skipped {name}: has character_id {cid!r}, uses its party sheet")
    if fails:
        print("GATE FAILURES:")
        for name, reasons in fails:
            print(f"  {name}: {reasons}")
    else:
        print("all gate-clean.")
    # the map the game needs: sheet stem -> the NPC it belongs to
    index = {sheet_key(n): {"map": n["map"], "node": n["node"], "npc_name": n["npc_name"]}
             for n in npcs if not n.get("character_id")}
    (out_dir / "index.json").write_text(json.dumps(index, indent=2), encoding="utf-8")


def _contact_sheet(written, path: Path):
    """South-facing idle per NPC, labelled. The point of this file is that a human can
    see at a glance that fifteen villagers still look like fifteen people."""
    F = ImageFont.load_default()
    CELL, GAP, LH, M, COLS = 72, 8, 22, 12, 6
    rows = (len(written) + COLS - 1) // COLS
    W = M * 2 + COLS * (CELL + GAP)
    H = M * 2 + 20 + rows * (CELL + LH + GAP)
    cs = Image.new("RGBA", (W, H), (34, 37, 44, 255))
    d = ImageDraw.Draw(cs)
    d.text((M, M), f"Vanguard placed NPCs via Meristem ({len(written)}), "
                   f"each from its own authored palette", fill=(232, 236, 244), font=F)
    for i, (key, npc, cfg) in enumerate(written):
        x = M + (i % COLS) * (CELL + GAP)
        y = M + 20 + (i // COLS) * (CELL + LH + GAP)
        d.rectangle([x, y, x + CELL - 1, y + CELL - 1], fill=(44, 48, 57, 255))
        idle = Image.fromarray(build_humanoid(C, cfg), "RGBA")
        cs.alpha_composite(idle.resize((CELL, CELL), Image.NEAREST), (x, y))
        d.text((x, y + CELL), npc["npc_name"][:13], fill=(150, 158, 172), font=F)
        d.text((x, y + CELL + 10), npc["map"][:13], fill=(120, 128, 142), font=F)
    cs.save(path)


if __name__ == "__main__":
    dump = Path(sys.argv[1])
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "build" / "vanguard-npcs"
    main(dump, out)
