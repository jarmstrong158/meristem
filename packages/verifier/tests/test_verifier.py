import json
import os
from pathlib import Path

import pytest

from meristem_verifier import derive_assertions, run_assertions, capture_frame
from meristem_verifier.critique import visual_expectations

MANIFEST = Path(__file__).resolve().parents[3] / "examples" / "slice-01" / "manifest.json"
GODOT = os.environ.get("MERISTEM_GODOT")


def _domains():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))["domains"]


# ---- always-on unit tests ----
def test_derive_move_speed_assertion():
    a = derive_assertions(_domains())
    assert len(a) == 1
    assert a[0]["kind"] == "move_speed" and a[0]["expected"] == 80.0


def test_no_assertions_without_matching_archetype():
    d = _domains()
    d["project"]["control_scheme"] = "does_not_exist"
    assert derive_assertions(d) == []


def test_visual_expectations_mentions_entities_and_palette():
    exp = " ".join(visual_expectations(_domains()))
    assert "PICO-8" in exp
    assert "Hero" in exp and "Slime" in exp
    assert "water" in exp.lower()          # enemy-not-on-water check present


# ---- real-engine tests (opt-in) ----
@pytest.fixture(scope="module")
def compiled(tmp_path_factory):
    from meristem_compiler.compile import compile_project
    out = tmp_path_factory.mktemp("verify-slice")
    compile_project(MANIFEST, out)
    return out


@pytest.mark.skipif(not GODOT, reason="set MERISTEM_GODOT to run the engine assertion loop")
def test_assertion_loop_measures_move_speed(compiled):
    res = run_assertions(compiled, derive_assertions(_domains()), GODOT)
    assert res["ok"], res
    r = res["results"][0]
    assert abs(r["measured"] - 80.0) <= 6.4


@pytest.mark.skipif(not GODOT, reason="set MERISTEM_GODOT to run the visual capture")
def test_visual_capture_produces_png(compiled):
    cap = capture_frame(compiled, GODOT)
    assert cap is not None and cap.exists()
    assert cap.stat().st_size > 200          # a real, non-empty PNG
