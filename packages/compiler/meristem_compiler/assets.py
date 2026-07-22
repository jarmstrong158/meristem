"""Compile the manifest's assets by ARCHETYPE (dec-0022).

Every entity/item declares `sprite: {archetype, config}`; the compiler dispatches to
the generator's archetype registry, gates the result, and writes a PNG + provenance
sidecar. Files are named by class-prefix + entity/item id (stable across archetypes).
"""
from __future__ import annotations

from pathlib import Path

from asset_gate import validate
from asset_gate.contract import StyleContract
from asset_gate.naming import asset_filename
from asset_gate.provenance import Provenance
from meristem_generators import archetype_class, archetype_frames, build_archetype

_HUD = [("heart", {"shape": "heart", "color": [226, 62, 84]}),
        ("coin", {"shape": "coin", "color": [240, 206, 84]})]


def compile_assets(domains: dict, assets_dir: str | Path) -> list[dict]:
    contract = StyleContract.from_dict(domains["style_contract"])
    assets_dir = Path(assets_dir)
    assets_dir.mkdir(parents=True, exist_ok=True)
    written: list[dict] = []

    def write_image(img, archetype, name_class, ident, variant, entity, frame=None):
        res = validate(img, archetype_class(archetype), contract)
        if not res.accepted:
            raise ValueError(f"{archetype}:{ident} {variant or ''} failed the gate: {res.reasons}")
        fname = asset_filename(contract, name_class, ident, variant)
        path = assets_dir / fname
        img.save(path)
        Provenance(backend=archetype, contract_name=contract.name, contract_hash=contract.hash(),
                   gate_version="0.1.0", source_sha256=Provenance.sha256_of_file(path)).write_sidecar(path)
        rec = {"archetype": archetype, "entity": entity or ident, "file": fname,
               "variant": variant, "class": name_class}
        if frame is not None:
            rec["frame"] = frame
        written.append(rec)
        return fname

    def emit(archetype, config, name_class, ident, variant=None, entity=None):
        return write_image(build_archetype(contract, archetype, config),
                            archetype, name_class, ident, variant, entity)

    def emit_frames(archetype, config, name_class, ident, entity, anim, skip0):
        # Animated archetypes: emit each frame. skip0 references an already-written
        # frame 0 (the idle/static PNG) so it isn't duplicated on disk.
        for i, fr in enumerate(archetype_frames(contract, archetype, config) or []):
            if skip0 and i == 0:
                continue
            write_image(fr, archetype, name_class, ident, f"{anim}_{i}", entity, frame=i)

    ents = domains.get("entities", {}) or {}
    for c in ents.get("characters", []):
        sp = c.get("sprite") or {"archetype": "humanoid"}
        cfg = sp.get("config", {})
        emit(sp["archetype"], cfg, "character", c["id"], "idle", entity=c["id"])
        emit_frames(sp["archetype"], cfg, "character", c["id"], c["id"], "walk", skip0=False)

    for e in ents.get("enemies", []):
        sp = e.get("sprite") or {"archetype": "blob"}
        cfg = sp.get("config", {})
        emit(sp["archetype"], cfg, "enemy", e["id"], "idle", entity=e["id"])
        emit_frames(sp["archetype"], cfg, "enemy", e["id"], e["id"], "anim", skip0=True)

    for it in (domains.get("items", {}) or {}).get("items", []):
        sp = it.get("sprite")
        if sp:
            emit(sp["archetype"], sp.get("config", {}), "item_icon", it["id"], entity=it["id"])

    for name, cfg in _HUD:                                           # fixed HUD pickups
        emit("pickup", cfg, "ui_element", name, entity=name)
        emit_frames("pickup", cfg, "ui_element", name, name, "spin", skip0=True)

    for a in contract.raw.get("asset_set", []):                     # terrain tiles
        if a.get("class") == "terrain_tile":
            emit("tile", {"name": a["name"]}, "terrain_tile", a["name"], entity=a["name"])

    return written
