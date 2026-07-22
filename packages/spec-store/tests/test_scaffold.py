import pytest

from meristem_spec_store import DOMAINS, scaffold_store, strawman
from meristem_spec_store.scaffold import _PARAMS
from meristem_spec_store.server import SpecService


@pytest.mark.parametrize("control", sorted(_PARAMS))
def test_strawman_is_valid_for_every_control(control):
    store = scaffold_store(title="T", control=control)
    report = store.validate_all()
    assert report.ok, report.to_dict()
    # all domains present
    assert set(store.domains) == set(DOMAINS)


def test_strawman_threads_answers_through():
    d = strawman(title="Grove Quest", control="top_down_controller",
                 protagonist="Mara", enemy="Bog Slime", biome="swamp")
    assert d["project"]["title"] == "Grove Quest"
    assert d["project"]["camera"] == "top_down"
    assert d["entities"]["characters"][0]["name"] == "Mara"
    assert d["entities"]["enemies"][0]["name"] == "Bog Slime"
    assert d["world"]["regions"][0]["biome"] == "swamp"


def test_platformer_gets_side_camera_and_jump_params():
    d = strawman(control="platformer_controller")
    assert d["project"]["camera"] == "side"
    assert "jump_height" in d["mechanics"]["archetypes"][0]["params"]


def test_unknown_control_rejected():
    with pytest.raises(ValueError):
        strawman(control="mech_piloting")


def test_scaffold_via_mcp_service(tmp_path):
    svc = SpecService(tmp_path / "m.json")
    res = svc.scaffold_project(title="Slime Grove", control="top_down_controller")
    assert res["accepted"]
    assert res["version"] == len(DOMAINS)
    assert svc.validate_all()["ok"]
