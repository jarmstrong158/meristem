"""Assertion loop: drive the compiled project headlessly and check spec-derived
assertions (state/physics, no pixels — true --headless works)."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

HARNESS = Path(__file__).parent / "harness"


def _install_harness(project_dir: Path, *files: str) -> Path:
    vdir = Path(project_dir) / "verifier"
    vdir.mkdir(parents=True, exist_ok=True)
    for f in files:
        shutil.copy(HARNESS / f, vdir / f)
    return vdir


def run_assertions(project_dir: str | Path, assertions: list[dict], godot_bin: str,
                   timeout: int = 120) -> dict:
    proj = Path(project_dir)
    vdir = _install_harness(proj, "verify.gd", "verify.tscn")
    (vdir / "assertions.json").write_text(json.dumps({"assertions": assertions}), encoding="utf-8")
    results_path = vdir / "results.json"
    if results_path.exists():
        results_path.unlink()

    subprocess.run([godot_bin, "--headless", "--path", str(proj), "--import"],
                   capture_output=True, text=True, timeout=timeout)
    proc = subprocess.run(
        [godot_bin, "--headless", "--path", str(proj), "res://verifier/verify.tscn",
         "--quit-after", "600"],
        capture_output=True, text=True, timeout=timeout)

    if not results_path.exists():
        return {"ok": False, "error": "harness produced no results.json",
                "stderr": proc.stderr[-1500:]}
    data = json.loads(results_path.read_text(encoding="utf-8"))
    results = data.get("results", [])
    return {"ok": bool(results) and all(r.get("ok") for r in results), "results": results}
