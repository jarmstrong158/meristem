"""Compile the manifest's assets: pick the backend per class (dec-0011:
surfaces->procedural, objects->agent-drawn), generate, gate, and write PNGs +
provenance sidecars into the Godot project."""
from __future__ import annotations

from pathlib import Path

from asset_gate import validate
from asset_gate.contract import StyleContract
from asset_gate.naming import asset_filename
from asset_gate.provenance import Provenance
from meristem_generators import AssetSpec, get

# dec-0011 assignment
_BACKEND = {"terrain_tile": "procedural", "character": "agent-drawn",
            "enemy": "agent-drawn", "item_icon": "agent-drawn", "ui_element": "agent-drawn"}
_HUD = ("heart", "coin")


def plan_assets(domains: dict, contract: StyleContract) -> list[tuple[AssetSpec, str]]:
    plan: list[tuple[AssetSpec, str]] = []
    ents = domains.get("entities", {}) or {}
    for c in ents.get("characters", []):
        if c.get("sprite"):
            plan.append((AssetSpec("character", c["sprite"], "idle"), _BACKEND["character"]))
    for e in ents.get("enemies", []):
        if e.get("sprite"):
            plan.append((AssetSpec("enemy", e["sprite"], "idle"), _BACKEND["enemy"]))
    for it in (domains.get("items", {}) or {}).get("items", []):
        if it.get("icon"):
            plan.append((AssetSpec("item_icon", it["icon"]), _BACKEND["item_icon"]))
    for ui in _HUD:
        plan.append((AssetSpec("ui_element", ui), _BACKEND["ui_element"]))
    for a in contract.raw.get("asset_set", []):
        if a.get("class") == "terrain_tile":
            plan.append((AssetSpec("terrain_tile", a["name"]), _BACKEND["terrain_tile"]))
    return plan


def compile_assets(domains: dict, assets_dir: str | Path) -> list[dict]:
    contract = StyleContract.from_dict(domains["style_contract"])
    assets_dir = Path(assets_dir)
    assets_dir.mkdir(parents=True, exist_ok=True)
    written: list[dict] = []
    for spec, backend in plan_assets(domains, contract):
        gen = get(backend)
        if not gen.supports(spec):
            raise ValueError(f"backend {backend!r} cannot generate {spec.asset_class}:{spec.name}")
        img = gen.generate(spec, contract)
        v = validate(img, spec.asset_class, contract)
        if not v.accepted:
            raise ValueError(f"generated {spec.name} failed the gate: {v.reasons}")
        fname = asset_filename(contract, spec.asset_class, spec.name, spec.variant)
        path = assets_dir / fname
        img.save(path)
        prov = Provenance(
            backend=backend, contract_name=contract.name, contract_hash=contract.hash(),
            gate_version="0.1.0", source_sha256=Provenance.sha256_of_file(path),
        )
        prov.write_sidecar(path)
        written.append({"class": spec.asset_class, "name": spec.name, "backend": backend,
                        "file": fname, "size": list(img.size)})
    return written
