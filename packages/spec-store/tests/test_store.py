import pytest

from meristem_spec_store import REQUIRED_DOMAINS, SpecStore, SpecValidationError
from meristem_spec_store.store import ValidationReport
from tests._data import consistent_domains


def build_store():
    s = SpecStore()
    for dom, val in consistent_domains().items():
        s.set_domain(dom, val, provenance={"actor": "test"})
    return s


def test_valid_write_bumps_version_and_records_history():
    s = build_store()
    assert s.version == 6
    assert len(s.history) == 6
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


def test_empty_manifest_is_invalid_not_vacuously_valid():
    """`validate_all` iterated only the domains that were PRESENT, so an empty
    manifest reported ok=True — and then the compiler died on domains["project"]
    with a bare KeyError. Absence is now a reported failure, not a silent pass."""
    report = SpecStore().validate_all()
    assert not report.ok
    assert set(report.missing_domains) == set(REQUIRED_DOMAINS)
    assert "missing required domain" in report.summary()
    assert report.to_dict()["missing_domains"] == report.missing_domains


def test_each_required_domain_is_individually_required():
    doms = consistent_domains()
    for required in REQUIRED_DOMAINS:
        s = SpecStore()
        for dom, val in doms.items():
            if dom != required:
                s.set_domain(dom, val)
        report = s.validate_all()
        assert report.missing_domains == [required], required
        assert not report.ok, required


def test_compiler_refuses_an_empty_manifest_with_an_actionable_error(tmp_path):
    from meristem_compiler.compile import CompileError, compile_project
    p = SpecStore().save(tmp_path / "manifest.json")
    with pytest.raises(CompileError) as ei:
        compile_project(p, tmp_path / "out")
    assert "missing required domain" in str(ei.value)      # not a bare KeyError: 'project'


def test_skipped_check_is_not_reported_as_a_passed_check():
    """A report is `ok` when no errors were FOUND and `complete` only when every
    check actually RAN. Conflating the two is how a skipped check greens a build."""
    r = ValidationReport(checks_skipped=["sprite_archetypes: generators not importable"])
    assert r.ok                       # nothing was found wrong...
    assert not r.complete             # ...but not everything was checked
    assert "SKIPPED" in r.summary()
    assert r.to_dict()["checks_skipped"] == r.checks_skipped
    assert r.to_dict()["complete"] is False
    clean = build_store().validate_all()
    assert clean.checks_skipped == [] and clean.complete


def test_crossref_records_a_skip_when_generators_are_missing(monkeypatch):
    """With `meristem-generators` a declared dependency this should never happen —
    but if the import does fail, the sprite/tile checks must land in checks_skipped
    rather than returning an empty (i.e. clean-looking) error list."""
    import builtins
    from meristem_spec_store.crossref import cross_reference

    real_import = builtins.__import__

    def blocked(name, *a, **kw):
        if name.startswith("meristem_generators"):
            raise ImportError("no meristem_generators")
        return real_import(name, *a, **kw)

    doms = consistent_domains()
    doms["levels"] = {"levels": [{"id": "forest_01", "region": "forest",
                                  "legend": {".": "grass"}, "rows": ["....", "...."],
                                  "player_spawn": {"x": 0, "y": 0}}]}
    monkeypatch.setattr(builtins, "__import__", blocked)
    errors, skipped = cross_reference(doms)
    assert errors == []
    assert len(skipped) == 2
    assert any("sprite_archetypes" in s for s in skipped)
    assert any("level_tiles" in s for s in skipped)


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
