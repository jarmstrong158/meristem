import pytest

from meristem_spec_store import SpecStore, SpecValidationError
from tests._data import consistent_domains


def build_store():
    s = SpecStore()
    for dom, val in consistent_domains().items():
        s.set_domain(dom, val, provenance={"actor": "test"})
    return s


def test_valid_write_bumps_version_and_records_history():
    s = build_store()
    assert s.version == 5
    assert len(s.history) == 5
    assert s.history[0]["provenance"] == {"actor": "test"}
    assert s.get("project")["title"] == "Test"


def test_invalid_write_is_rejected_not_coerced():
    s = SpecStore()
    with pytest.raises(SpecValidationError) as ei:
        s.set_domain("project", {"title": "x", "genre": "g", "camera": "vr",
                                 "control_scheme": "c", "core_loop": "l",
                                 "target_resolution": {"w": 1, "h": 1}})
    assert ei.value.domain == "project"
    assert s.version == 0            # nothing stored
    assert s.get("project") is None


def test_unknown_domain_rejected():
    s = SpecStore()
    with pytest.raises(KeyError):
        s.set_domain("spaceships", {})


def test_validate_all_passes_on_consistent_manifest():
    report = build_store().validate_all()
    assert report.ok, report.to_dict()


def test_crossref_catches_dangling_drop_reference():
    s = build_store()
    # schema-valid items, but drops from an enemy that doesn't exist
    bad_items = consistent_domains()["items"]
    bad_items["drop_tables"][0]["enemy_id"] = "dragon"
    s.set_domain("items", bad_items)     # accepted (schema-valid)
    report = s.validate_all()
    assert not report.ok
    assert any("dragon" in e for e in report.crossref_errors)


def test_crossref_catches_bad_behavior_archetype():
    s = build_store()
    ents = consistent_domains()["entities"]
    ents["enemies"][0]["behavior_archetype"] = "flying"
    s.set_domain("entities", ents)
    report = s.validate_all()
    assert any("flying" in e for e in report.crossref_errors)


def test_save_load_roundtrip(tmp_path):
    s = build_store()
    p = s.save(tmp_path / "manifest.json")
    s2 = SpecStore.load(p)
    assert s2.version == s.version
    assert s2.get_all() == s.get_all()
    assert s2.validate_all().ok


def test_diff_reports_changes():
    s = build_store()
    cand = consistent_domains()["project"]
    cand["title"] = "Renamed"
    d = s.diff_domain("project", cand)
    assert d["has_changes"]
    assert "title" in d["changed"]
    assert d["changed"]["title"] == ["Test", "Renamed"]
