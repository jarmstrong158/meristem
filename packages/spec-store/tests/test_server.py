import pytest

from meristem_spec_store.server import SpecService, build_server
from tests._data import consistent_domains


@pytest.fixture
def svc(tmp_path):
    return SpecService(tmp_path / "manifest.json")


def test_set_domain_accepts_and_persists(svc, tmp_path):
    doms = consistent_domains()
    res = svc.set_domain("mechanics", doms["mechanics"], actor="tester", reason="init")
    assert res["accepted"] and res["version"] == 1
    # a fresh service on the same file sees the persisted write
    again = SpecService(tmp_path / "manifest.json")
    assert again.get_domain("mechanics")["value"] is not None


def test_set_domain_rejects_with_errors(svc):
    res = svc.set_domain("project", {"title": "x", "genre": "g", "camera": "vr",
                                     "control_scheme": "c", "core_loop": "l",
                                     "target_resolution": {"w": 1, "h": 1}})
    assert res["accepted"] is False
    assert res["domain"] == "project"
    assert res["errors"]


def test_validate_all_via_service(svc):
    for dom, val in consistent_domains().items():
        assert svc.set_domain(dom, val)["accepted"]
    assert svc.validate_all()["ok"]


def test_unknown_domain_read(svc):
    assert "error" in svc.get_domain("nope")


def test_build_server_registers_tools(tmp_path):
    svc = SpecService(tmp_path / "m.json")
    mcp = build_server(svc)
    # FastMCP exposes registered tools; names should include our set
    import asyncio
    tools = asyncio.run(mcp.list_tools())
    names = {t.name for t in tools}
    assert {"list_domains", "get_domain", "get_manifest", "set_domain",
            "diff_domain", "validate_all", "scaffold_project", "inspect_manifest",
            "list_sprite_archetypes", "check_sprite"} <= names


def test_mcp_apps_ui_resource_registered(tmp_path):
    import asyncio
    from meristem_spec_store.server import SPEC_INSPECTOR_URI
    svc = SpecService(tmp_path / "m.json")
    mcp = build_server(svc)
    resources = asyncio.run(mcp.list_resources())
    match = [r for r in resources if str(r.uri) == SPEC_INSPECTOR_URI]
    assert match, [str(r.uri) for r in resources]
    # SEP-1865 Final mimeType (verified)
    assert match[0].mimeType == "text/html;profile=mcp-app"


def test_list_sprite_archetypes(svc):
    res = svc.list_sprite_archetypes()
    assert res["available"], res
    by = {a["archetype"]: a for a in res["archetypes"]}
    assert {"flyer", "spider", "weapon", "humanoid", "tile"} <= set(by)
    assert "bat" in by["flyer"]["variants"]["build"] and by["flyer"]["animated"]
    assert by["flyer"]["class"] == "enemy"


def test_check_sprite(svc):
    assert svc.check_sprite("flyer", {"build": "bat"}) == {"available": True, "ok": True, "problems": []}
    bad = svc.check_sprite("flyer", {"build": "dragon"})
    assert bad["available"] and not bad["ok"] and bad["problems"]
    assert not svc.check_sprite("nonexistent", {})["ok"]


def test_validate_all_rejects_bogus_sprite_build(svc):
    for dom, val in consistent_domains().items():
        assert svc.set_domain(dom, val)["accepted"]
    assert svc.validate_all()["ok"]                          # baseline is coherent
    # a typo'd build is schema-valid (config is a free object) but not a real build
    ents = svc.get_domain("entities")["value"]
    ents["enemies"][0]["sprite"] = {"archetype": "flyer", "config": {"build": "dragon"}}
    assert svc.set_domain("entities", ents)["accepted"]      # per-domain schema passes it
    report = svc.validate_all()
    assert not report["ok"]                                  # ...but the manifest is now invalid
    assert any("dragon" in e for e in report["crossref_errors"])


def test_inspector_payload_shape(tmp_path):
    from meristem_spec_store.server import _inspector_payload
    svc = SpecService(tmp_path / "m.json")
    svc.scaffold_project(title="Panel Test")
    payload = _inspector_payload(svc.store)
    assert payload["validation"]["ok"]
    assert payload["domains"]["project"] is True
    assert "project" in payload["present"]
