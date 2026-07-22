"""CLI: compile a manifest into a Godot 4 project.

    meristem-compile examples/slice-01/manifest.json --out build/slice-01
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .compile import CompileError, compile_project


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="meristem-compile",
                                description="Compile a manifest into a Godot 4 project.")
    p.add_argument("manifest", help="path to the manifest JSON (spec-store format)")
    p.add_argument("--out", required=True, help="output project directory")
    p.add_argument("--json", action="store_true", help="emit JSON summary")
    args = p.parse_args(argv)

    if not Path(args.manifest).exists():
        print(f"manifest not found: {args.manifest}", file=sys.stderr)
        return 1
    try:
        summary = compile_project(args.manifest, args.out)
    except CompileError as e:
        print(f"compile error: {e}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(f"compiled '{summary['title']}' -> {summary['project_dir']} "
              f"({summary['assets']} assets, {summary['level']['tiles']} tiles)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
