"""CLI: verify a compiled project against its manifest.

    meristem-verify build/slice-01 --manifest examples/slice-01/manifest.json \\
        --godot /path/to/godot [--visual]

Assertion loop always runs (headless). --visual also captures a rendered frame and
prints the spec-derived expectations for a vision-model critique.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from meristem_spec_store import SpecStore

from .assertions import derive_assertions
from .critique import visual_expectations
from .runner import run_assertions
from .visual import capture_frame


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="meristem-verify",
                                description="Verify a compiled project against its manifest.")
    p.add_argument("project_dir")
    p.add_argument("--manifest", required=True)
    p.add_argument("--godot", required=True, help="path to a Godot 4.x binary")
    p.add_argument("--visual", action="store_true", help="also capture a frame + print expectations")
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    domains = SpecStore.load(args.manifest).get_all()
    assertions = derive_assertions(domains)
    result = run_assertions(args.project_dir, assertions, args.godot)

    out = {"assertions": result}
    if args.visual:
        cap = capture_frame(args.project_dir, args.godot)
        out["visual"] = {"capture": str(cap) if cap else None,
                         "expectations": visual_expectations(domains)}

    if args.json:
        print(json.dumps(out, indent=2))
    else:
        status = "PASS" if result["ok"] else "FAIL"
        print(f"[assertions {status}]")
        for r in result.get("results", []):
            mark = "ok" if r.get("ok") else "XX"
            print(f"  [{mark}] {r.get('kind')} {r.get('entity','')}: "
                  f"expected {r.get('expected')} measured {r.get('measured')}")
        if args.visual and out["visual"]["capture"]:
            print(f"captured {out['visual']['capture']} — critique against:")
            for e in out["visual"]["expectations"]:
                print(f"  - {e}")
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
