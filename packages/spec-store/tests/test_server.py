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
    # FastMCP exposes registered tools; names should include our six
    import asyncio
    tools = asyncio.run(mcp.list_tools())
    names = {t.name for t in tools}
    assert {"list_domains", "get_domain", "get_manifest", "set_domain",
            "diff_domain", "validate_all"} <= names
