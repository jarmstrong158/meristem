#!/usr/bin/env python3
"""Meristem self-installer — bring the whole suite up on a fresh machine.

The Claude Code plugin ships only the skills, commands, and this script; the
actual engine (the meristem_* Python packages, the generators, tools, and
example project) lives in the repo. So `/plugin install` alone is not enough:
the MCP server (`python -m meristem_spec_store.server`) and the pixel-art skill
(`sprite_catalog()`, the asset gate) would fail with ModuleNotFoundError.

This script closes that gap, using ONLY the Python standard library so it can
run before anything is installed:

  1. find a Python >= 3.10 to build a venv with,
  2. clone (or update) the whole Meristem suite to a home dir (default ~/.meristem),
  3. create an isolated venv there and pip-install all 5 packages editable
     (spec-store with its [mcp] extra so the MCP server has its deps),
  4. repoint the installed plugin's .mcp.json at that venv's Python, so the
     spec-store MCP actually starts,
  5. write ENVIRONMENT.md (paths the skills should use),
  6. run a doctor: import checks + a live sprite-catalog smoke test.

Re-runnable and idempotent. `--doctor` runs only step 6.

Usage (normally invoked by the /meristem-setup command):
    python install.py --plugin-root "<CLAUDE_PLUGIN_ROOT>"
    python install.py --doctor
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO_URL = "https://github.com/jarmstrong158/meristem.git"
DEFAULT_HOME = Path.home() / ".meristem"
# install order is not load-bearing (setuptools resolves), but keep engine first
PACKAGES = ["generators", "asset-gate", "spec-store[mcp]", "compiler", "verifier"]
MIN_PY = (3, 10)


# ---- tiny output helpers (no color deps; plain ASCII so no charmap issues) ----
def say(msg: str) -> None:
    print(f"[meristem] {msg}", flush=True)


def die(msg: str) -> int:
    print(f"[meristem] ERROR: {msg}", file=sys.stderr, flush=True)
    return 1


def run(cmd: list, **kw) -> subprocess.CompletedProcess:
    say("+ " + " ".join(str(c) for c in cmd))
    return subprocess.run(cmd, check=True, **kw)


# ---- paths ----
def venv_python(home: Path) -> Path:
    v = home / ".venv"
    return v / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


# ---- steps ----
def find_base_python() -> str:
    """A Python >= 3.10 to build the venv. Prefer the interpreter running us."""
    if sys.version_info >= MIN_PY:
        return sys.executable
    for cand in ("python3.13", "python3.12", "python3.11", "python3.10", "python3", "python"):
        exe = shutil.which(cand)
        if not exe:
            continue
        try:
            out = subprocess.run([exe, "-c", "import sys;print('%d.%d' % sys.version_info[:2])"],
                                 capture_output=True, text=True, check=True).stdout.strip()
            major, minor = (int(x) for x in out.split("."))
            if (major, minor) >= MIN_PY:
                return exe
        except Exception:
            continue
    raise RuntimeError(
        f"need Python {MIN_PY[0]}.{MIN_PY[1]}+ but none was found on PATH. "
        "Install it from https://www.python.org/downloads/ and re-run /meristem-setup."
    )


def sync_repo(home: Path, source: str, branch: str) -> None:
    """Clone the whole suite to `home`, or update it if already there."""
    if (home / ".git").exists():
        say(f"updating existing checkout at {home}")
        run(["git", "-C", str(home), "fetch", "--depth", "1", "origin", branch])
        run(["git", "-C", str(home), "checkout", branch])
        run(["git", "-C", str(home), "reset", "--hard", f"origin/{branch}"])
    else:
        if home.exists() and any(home.iterdir()):
            raise RuntimeError(f"{home} exists and is not a git checkout; move it aside and re-run.")
        home.parent.mkdir(parents=True, exist_ok=True)
        say(f"cloning {source} ({branch}) -> {home}")
        run(["git", "clone", "--depth", "1", "--branch", branch, source, str(home)])


def make_venv(home: Path, base_python: str) -> Path:
    vpy = venv_python(home)
    if not vpy.exists():
        say(f"creating venv at {home / '.venv'}")
        run([base_python, "-m", "venv", str(home / ".venv")])
    run([str(vpy), "-m", "pip", "install", "--quiet", "--upgrade", "pip"])
    return vpy


def pip_install_packages(home: Path, vpy: Path) -> None:
    targets = []
    for spec in PACKAGES:
        # "spec-store[mcp]" -> path "packages/spec-store" + "[mcp]"
        name, _, extra = spec.partition("[")
        path = home / "packages" / name
        if not path.exists():
            raise RuntimeError(f"expected package dir missing: {path}")
        targets += ["-e", str(path) + (f"[{extra}" if extra else "")]
    say("installing packages into the venv (editable): " + ", ".join(PACKAGES))
    run([str(vpy), "-m", "pip", "install", "--quiet", *targets])


def patch_mcp(plugin_root: Path, vpy: Path) -> bool:
    """Repoint the plugin's spec-store MCP at the venv Python so it can import
    its deps. Returns True if a file was written."""
    mcp_path = plugin_root / ".mcp.json"
    if not mcp_path.exists():
        say(f"note: no .mcp.json at {mcp_path}; skipping MCP repoint")
        return False
    data = json.loads(mcp_path.read_text(encoding="utf-8"))
    srv = data.get("mcpServers", {}).get("meristem-spec-store")
    if not srv:
        say("note: meristem-spec-store not declared in .mcp.json; skipping")
        return False
    srv["command"] = str(vpy)
    srv["args"] = ["-m", "meristem_spec_store.server"]
    mcp_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    say(f"repointed spec-store MCP -> {vpy}")
    return True


def write_environment(home: Path, vpy: Path) -> None:
    (home / "ENVIRONMENT.md").write_text(
        "# Meristem environment (generated by install.py)\n\n"
        f"- Suite checkout: `{home}`\n"
        f"- Python venv:   `{home / '.venv'}`\n"
        f"- venv python:   `{vpy}`\n\n"
        "Skills and tools should use the venv python above, e.g.:\n\n"
        "```\n"
        f'"{vpy}" "{home / "tools" / "contact_sheet.py"}"\n'
        f'"{vpy}" -m meristem_spec_store.server\n'
        "```\n\n"
        "Compile a manifest to a Godot project:\n\n"
        "```\n"
        f'"{vpy}" -m meristem_compiler <manifest.json> --out build/my-game\n'
        "```\n",
        encoding="utf-8",
    )
    say(f"wrote {home / 'ENVIRONMENT.md'}")


def doctor(home: Path) -> int:
    vpy = venv_python(home)
    say(f"doctor: checking {home}")
    if not vpy.exists():
        return die(f"venv python not found at {vpy}; run /meristem-setup first.")
    checks = [
        ("import generators", "import meristem_generators"),
        ("import asset gate", "import asset_gate"),
        ("import spec-store", "import meristem_spec_store"),
        ("import mcp dep", "import mcp"),
        ("sprite catalog", "from meristem_generators import sprite_catalog; "
                           "print('archetypes=%d' % len(sprite_catalog()))"),
        ("humanoid props", "from meristem_generators import sprite_catalog; "
                           "h=[a for a in sprite_catalog() if a['archetype']=='humanoid'][0]; "
                           "assert 'held' in h['variants'] and 'garment' in h['variants']; "
                           "print('prop axes ok:', sorted(h['variants']))"),
    ]
    ok = True
    for label, code in checks:
        try:
            out = subprocess.run([str(vpy), "-c", code], capture_output=True, text=True, check=True)
            tail = out.stdout.strip().splitlines()[-1] if out.stdout.strip() else "ok"
            say(f"  PASS  {label}: {tail}")
        except subprocess.CalledProcessError as e:
            ok = False
            say(f"  FAIL  {label}: {(e.stderr or e.stdout or '').strip().splitlines()[-1:] }")
    if ok:
        say("doctor: ALL GREEN. The engine is installed and the MCP can start.")
        say("If the spec-store MCP shows as failed, reload it (restart Claude Code or /mcp) "
            "so it picks up the repointed interpreter.")
        return 0
    return die("doctor found problems (see FAIL lines above).")


def install(home: Path, plugin_root: Path | None, source: str, branch: str) -> int:
    if not shutil.which("git"):
        return die("git is required but was not found on PATH. Install git and re-run /meristem-setup.")
    try:
        base = find_base_python()
        say(f"using base Python: {base}")
        sync_repo(home, source, branch)
        vpy = make_venv(home, base)
        pip_install_packages(home, vpy)
        if plugin_root:
            patch_mcp(Path(plugin_root), vpy)
        write_environment(home, vpy)
    except (RuntimeError, subprocess.CalledProcessError) as e:
        return die(str(e))
    say("install complete.")
    return doctor(home)


def main() -> int:
    ap = argparse.ArgumentParser(description="Meristem self-installer")
    ap.add_argument("--home", default=str(DEFAULT_HOME), help="suite install dir (default ~/.meristem)")
    ap.add_argument("--plugin-root", default=os.environ.get("CLAUDE_PLUGIN_ROOT"),
                    help="installed plugin dir whose .mcp.json to repoint")
    ap.add_argument("--source", default=REPO_URL, help="git URL or local path to clone from")
    ap.add_argument("--branch", default="main", help="branch to install (default main)")
    ap.add_argument("--doctor", action="store_true", help="run only the health check")
    args = ap.parse_args()
    home = Path(args.home).expanduser()
    if args.doctor:
        return doctor(home)
    return install(home, args.plugin_root, args.source, args.branch)


if __name__ == "__main__":
    raise SystemExit(main())
