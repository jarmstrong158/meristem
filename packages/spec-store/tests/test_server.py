import pytest

import pytest

from meristem_spec_store.server import (McpUnavailable, SpecService,
                                        build_server)


def _server(svc):
    """build_server, skipped rather than failed when the optional MCP extra is
    absent or is a version whose FastMCP this cannot find. An OPTIONAL extra
    must not be able to fail the suite -- an upstream release that moved
    FastMCP turned every one of these red on a commit that touched no Python."""
    try:
        return build_server(svc)
    except McpUnavailable as exc:
        pytest.skip(str(exc))
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
    mcp = _server(svc)
    # FastMCP exposes registered tools; names should include our set
    import asyncio
    tools = asyncio.run(mcp.list_tools())
    names = {t.name for t in tools}
    assert {"list_domains", "get_domain", "get_manifest", "set_domain",
            "diff_domain", "validate_all", "scaffold_project", "inspect_manifest",
            "list_sprite_archetypes", "check_sprite",
            "preview_sprite", "compare_builds"} <= names


def test_mcp_apps_ui_resource_registered(tmp_path):
    import asyncio
    from meristem_spec_store.server import SPEC_INSPECTOR_URI
    svc = SpecService(tmp_path / "m.json")
    mcp = _server(svc)
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
    assert svc.check_sprite("flyer", {"build": "bat"}) == {
        "available": True, "ok": True, "problems": [], "warnings": [],
        "checks_skipped": []}
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


def test_scaffold_includes_playable_level(svc):
    res = svc.scaffold_project(title="Level Test")
    assert res["accepted"]
    lv = svc.get_domain("levels")["value"]["levels"][0]
    assert lv["region"] == "start_region" and len(lv["rows"]) >= 8
    kinds = {s["kind"] for s in lv["spawns"]}
    assert kinds == {"enemy", "item"}                    # enemies to fight + a pickup


def test_level_crossref_rejects_incoherence(svc):
    for dom, val in consistent_domains().items():
        assert svc.set_domain(dom, val)["accepted"]
    base = {"id": "lv1", "region": "start", "legend": {".": "grass"},
            "rows": ["....", "...."], "player_spawn": {"x": 0, "y": 0}}
    region = consistent_domains()["world"]["regions"][0]["id"]

    def check(patch, expect):
        lv = {**base, **patch, "region": patch.get("region", region)}
        assert svc.set_domain("levels", {"levels": [lv]})["accepted"]   # schema-valid
        report = svc.validate_all()
        assert not report["ok"]
        assert any(expect in e for e in report["crossref_errors"]), report["crossref_errors"]

    check({"region": "nowhere"}, "not a world region")
    check({"rows": ["....", "..."]}, "length")                       # ragged rows
    check({"rows": ["..x.", "...."]}, "not in the legend")           # unknown char
    check({"legend": {".": "cheese"}}, "not a known tile")           # bogus tile
    check({"player_spawn": {"x": 9, "y": 0}}, "outside")             # OOB spawn
    check({"spawns": [{"id": "dragon", "kind": "enemy", "x": 1, "y": 1}]}, "does not resolve")


def test_check_sprite_warns_on_config_keys_the_archetype_ignores(svc):
    """A typo'd config KEY validated completely clean and then rendered the default.
    It is a warning, not an error: the sprite still builds, it just quietly ignores
    what the author wrote — which is harder to notice than a failure."""
    res = svc.check_sprite("pickup", {"shape": "heart", "shpae": "gem"})
    assert res["ok"] and not res["problems"]                 # still renders, so not an error
    assert any("shpae" in w for w in res["warnings"])
    assert svc.check_sprite("pickup", {"shape": "heart"})["warnings"] == []
    # the British-spelling trap on a colour knob
    brit = svc.check_sprite("humanoid", {"hat_colour": (1, 2, 3)})
    assert any("hat_colour" in w for w in brit["warnings"])
    # a per-frame animation knob is legitimate and must not be warned about
    assert svc.check_sprite("quadruped", {"build": "dog", "head_dy": 1})["warnings"] == []


def test_preview_sprite_reports_a_missing_style_contract(svc):
    """No contract in the manifest means nothing to render against — say so rather
    than invent a default, or the preview shows a different game than the build."""
    res = svc.preview_sprite("blob")
    assert not res["ok"] and "style_contract" in res["reason"]
    assert "png" not in res


def test_preview_sprite_renders_against_the_manifests_contract(svc):
    assert svc.scaffold_project(title="Preview Test")["accepted"]
    res = svc.preview_sprite("quadruped", {"build": "boar"}, scale=4)
    assert res["ok"], res
    assert res["png"][:8] == b"\x89PNG\r\n\x1a\n"
    assert res["native_size"] == [32, 32] and res["asset_class"] == "enemy"
    assert res["frames"] == 4 and res["scale"] == 4
    assert res["gate"]["accepted"] is True, res["gate"]


def test_preview_refuses_a_descriptor_that_would_silently_fall_back(svc):
    """A typo'd build renders the archetype's DEFAULT, so previewing it would show a
    dog captioned 'griffon' and read as confirmation that the build exists."""
    assert svc.scaffold_project(title="Preview Test")["accepted"]
    res = svc.preview_sprite("quadruped", {"build": "griffon"})
    assert not res["ok"] and res["problems"]
    assert "png" not in res


def test_compare_builds_covers_every_variant_of_the_archetype(svc):
    assert svc.scaffold_project(title="Preview Test")["accepted"]
    res = svc.compare_builds("projectile", scale=3)
    assert res["ok"], res
    assert res["variant_key"] == "kind"
    assert set(res["builds"]) == {"arrow", "fireball", "bolt", "knife", "shuriken"}
    assert res["silhouette"] is True                          # the distinctness question
    assert res["png"][:8] == b"\x89PNG\r\n\x1a\n"


def test_preview_tools_emit_real_image_content(tmp_path):
    """The whole point is that the caller can SEE the sprite, so these must come back
    as image content — a base64 string buried in text would not be looked at."""
    import asyncio
    from mcp.types import ImageContent
    svc = SpecService(tmp_path / "m.json")
    assert svc.scaffold_project(title="Image Test")["accepted"]
    mcp = _server(svc)
    assert {"preview_sprite", "compare_builds"} <= {t.name for t in asyncio.run(mcp.list_tools())}
    for tool, args in (("preview_sprite", {"archetype": "blob", "scale": 3}),
                       ("compare_builds", {"archetype": "flyer", "scale": 3})):
        out = asyncio.run(mcp.call_tool(tool, args))
        parts = out[0] if isinstance(out, tuple) else out
        images = [c for c in parts if isinstance(c, ImageContent)]
        assert images, (tool, parts)
        assert images[0].mimeType == "image/png"
        assert images[0].data                                 # base64 payload present


def test_inspector_payload_shape(tmp_path):
    from meristem_spec_store.server import _inspector_payload
    svc = SpecService(tmp_path / "m.json")
    svc.scaffold_project(title="Panel Test")
    payload = _inspector_payload(svc.store)
    assert payload["validation"]["ok"]
    assert payload["domains"]["project"] is True
    assert "project" in payload["present"]
