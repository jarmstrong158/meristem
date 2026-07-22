"""Spec-derived expectations for the visual loop: a checklist a vision model uses
to critique the captured frame. A clean compile is not evidence; the pixels must
match the spec (assets present, on-palette, readable, correctly placed)."""
from __future__ import annotations


def visual_expectations(domains: dict) -> list[str]:
    exp: list[str] = []
    contract = domains.get("style_contract", {})
    pal = contract.get("palette", {}).get("source", "the locked palette")
    exp.append(f"Every pixel is within {pal} (no off-palette or anti-aliased colors).")

    ents = domains.get("entities", {})
    for c in ents.get("characters", []):
        exp.append(f"The {c['name']} character is visible and reads clearly at 1x.")
    for e in ents.get("enemies", []):
        exp.append(f"The {e['name']} enemy is visible and NOT standing on impassable terrain (e.g. water).")

    world = domains.get("world", {})
    biomes = ", ".join(sorted({r.get("biome", "") for r in world.get("regions", [])}))
    if biomes:
        exp.append(f"The ground is tiled terrain ({biomes}); tiles align to the grid with no gaps or seams.")

    exp.append("HUD elements (e.g. heart, coin) are visible and unobstructed in a corner.")
    exp.append("No missing-texture placeholders, z-order faults, or unreadable silhouettes.")
    return exp
