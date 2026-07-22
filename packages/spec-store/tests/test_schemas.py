import json
from pathlib import Path

import pytest

from meristem_spec_store import DOMAINS, validate_domain
from meristem_spec_store.schemas import find_schema_dir, load_validators


def test_all_domain_schemas_load():
    v = load_validators()
    assert set(v) == set(DOMAINS)


def test_real_style_contract_validates():
    contract = find_schema_dir().parent / "experiments" / "00-bakeoff" / "style-contract.json"
    data = json.loads(contract.read_text(encoding="utf-8"))
    assert validate_domain("style_contract", data) == []


def test_mechanics_conditional_params():
    # platformer requires jump_height
    bad = {"archetypes": [{"id": "hero", "kind": "platformer_controller",
                           "params": {"move_speed": 100, "accel": 500, "gravity": 900}}]}
    errs = validate_domain("mechanics", bad)
    assert errs, "missing jump_height should fail"

    good = {"archetypes": [{"id": "hero", "kind": "platformer_controller",
                            "params": {"move_speed": 100, "accel": 500, "jump_height": 48, "gravity": 900}}]}
    assert validate_domain("mechanics", good) == []


def test_sprite_descriptor_validation():
    base = {"id": "hero", "name": "Hero", "stats": {"hp": 1}}
    ok = {"characters": [{**base, "sprite": {"archetype": "humanoid"}}]}
    assert validate_domain("entities", ok) == []
    bad_arch = {"characters": [{**base, "sprite": {"archetype": "dragon"}}]}
    assert validate_domain("entities", bad_arch)                 # unknown archetype -> error
    no_arch = {"characters": [{**base, "sprite": {"config": {}}}]}
    assert validate_domain("entities", no_arch)                  # archetype is required
    # items carry the same descriptor
    item_ok = {"items": [{"id": "wp", "name": "Blade", "slot": "weapon",
                          "sprite": {"archetype": "weapon", "config": {"kind": "greatsword"}}}]}
    assert validate_domain("items", item_ok) == []


def test_project_enum_rejected():
    bad = {"title": "T", "genre": "rpg", "camera": "vr", "control_scheme": "x",
           "core_loop": "loop", "target_resolution": {"w": 320, "h": 180}}
    assert any("camera" in e for e in validate_domain("project", bad))
