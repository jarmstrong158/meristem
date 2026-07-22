import pytest

from asset_gate import load_contract
from asset_gate.contract import ContractError, StyleContract
from asset_gate.naming import asset_filename


def test_loads_fixture(contract):
    assert contract.name == "test-fixture-v1"
    assert contract.canvas_of("item_icon") == (16, 16)
    assert contract.canvas_of("character") == (32, 32)
    assert contract.anchor_of("terrain_tile") == "top_left"
    assert contract.anchor_of("item_icon") == "center"
    assert contract.palette_rgb.shape == (6, 3)


def test_unknown_class_raises(contract):
    with pytest.raises(ContractError):
        contract.canvas_of("spaceship")


def test_hash_is_stable_and_content_sensitive(contract):
    h1 = contract.hash()
    assert h1.startswith("sha256:")
    assert contract.hash() == h1  # stable across calls
    mutated = dict(contract.raw)
    mutated["version"] = 999
    assert StyleContract.from_dict(mutated).hash() != h1


def test_missing_key_is_contract_error():
    with pytest.raises(ContractError):
        StyleContract.from_dict({"name": "x"})  # no palette/canvas


def test_naming(contract):
    assert asset_filename(contract, "item_icon", "sword") == "icon_sword.png"
    assert asset_filename(contract, "character", "player", "idle") == "char_player_idle.png"
