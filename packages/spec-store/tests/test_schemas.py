import json
from pathlib import Path

import pytest

from meristem_spec_store import DOMAINS, validate_domain
from meristem_spec_store.schemas import _schema_filename, find_schema_dir, load_validators


def test_every_schema_file_is_a_registered_domain():
    """This used to assert `set(load_validators()) == set(DOMAINS)` — but
    `load_validators()` BUILDS its dict by iterating `DOMAINS`, so the assertion was
    a tautology that could not fail. The real risk is a schema file that exists on
    disk and is wired to nothing (or a DOMAINS entry with no file), so compare
    `DOMAINS` against the DIRECTORY."""
    sdir = find_schema_dir()
    on_disk = {p.name for p in sdir.glob("*.schema.json")}
    registered = {_schema_filename(d) for d in DOMAINS}
    assert on_disk == registered, {
        "unregistered files": sorted(on_disk - registered),
        "registered but missing from disk": sorted(registered - on_disk),
    }
    # and each one really loads as a Draft 2020-12 validator
    assert set(load_validators()) == set(DOMAINS)


ARCHETYPE_ENUM_SITES = [("entities.schema.json", "sprite"), ("items.schema.json", "sprite")]


@pytest.mark.parametrize("filename,defname", ARCHETYPE_ENUM_SITES)
def test_schema_archetype_enum_matches_the_live_generator_registry(filename, defname):
    """The sprite `archetype` enum is duplicated in two schema files and hand-written,
    while the real list lives in the generator registry. Nothing but this test connects
    them: add an archetype (as `raptor`/`beetle` were added) and the schemas silently
    keep rejecting it; remove one and the schemas keep advertising a build that no
    longer exists. Both failures land on a manifest author as a confusing error."""
    # NOT importorskip: `meristem-generators` is a declared dependency of the spec
    # store (dec-0036), and skipping the repo's highest-value drift test on an import
    # failure would be the same mistake the validation report used to make.
    from meristem_generators import known_archetypes
    live = set(known_archetypes())
    schema = json.loads((find_schema_dir() / filename).read_text(encoding="utf-8"))
    enum = set(schema["$defs"][defname]["properties"]["archetype"]["enum"])
    assert enum == live, {
        "in the registry but rejected by the schema": sorted(live - enum),
        "allowed by the schema but not buildable": sorted(enum - live),
    }


def test_both_schema_archetype_enums_agree_with_each_other():
    enums = []
    for filename, defname in ARCHETYPE_ENUM_SITES:
        schema = json.loads((find_schema_dir() / filename).read_text(encoding="utf-8"))
        enums.append(set(schema["$defs"][defname]["properties"]["archetype"]["enum"]))
    assert enums[0] == enums[1], sorted(enums[0] ^ enums[1])


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
