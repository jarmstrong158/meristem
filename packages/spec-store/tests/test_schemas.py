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


def test_project_enum_rejected():
    bad = {"title": "T", "genre": "rpg", "camera": "vr", "control_scheme": "x",
           "core_loop": "loop", "target_resolution": {"w": 320, "h": 180}}
    assert any("camera" in e for e in validate_domain("project", bad))
