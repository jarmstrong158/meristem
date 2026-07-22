"""Standalone CLI for the asset gate.

    asset-gate normalize INPUT.png --class item_icon --contract contract.json [--out OUT.png]
    asset-gate validate  INPUT.png --class item_icon --contract contract.json

Exit codes: 0 accepted, 2 rejected, 1 usage/error.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from PIL import Image

from .contract import ContractError, load_contract
from .gate import normalize, validate
from .provenance import Provenance


def _print_result(res, as_json: bool) -> None:
    if as_json:
        print(json.dumps({
            "accepted": res.accepted,
            "asset_class": res.asset_class,
            "reasons": res.reasons,
            "warnings": res.warnings,
            "report": res.report,
        }, indent=2))
        return
    status = "ACCEPTED" if res.accepted else "REJECTED"
    print(f"[{status}] {res.asset_class}")
    for w in res.warnings:
        print(f"  warning: {w}")
    for r in res.reasons:
        print(f"  reason:  {r}")
    if res.report:
        rp = res.report
        print(f"  size={rp.get('size')} palette={rp.get('palette_exact_pct')}% "
              f"uniq={rp.get('unique_colors')} semi_alpha={rp.get('semi_transparent_px')} "
              f"coverage={rp.get('coverage')}")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="asset-gate", description="Normalize an image to a style contract, or reject it.")
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(sp):
        sp.add_argument("input", help="input image path")
        sp.add_argument("--class", dest="asset_class", required=True, help="asset class in the contract")
        sp.add_argument("--contract", required=True, help="style contract JSON path")
        sp.add_argument("--json", action="store_true", help="emit JSON report")

    n = sub.add_parser("normalize", help="normalize-or-reject and write the asset")
    common(n)
    n.add_argument("--out", help="output PNG path (default: <input>.gated.png)")
    n.add_argument("--quantize", default="nearest", choices=["nearest", "nearest_dither"])
    grp = n.add_mutually_exclusive_group()
    grp.add_argument("--outline", dest="outline", action="store_true", default=None)
    grp.add_argument("--no-outline", dest="outline", action="store_false")
    n.add_argument("--backend", default="imported", help="provenance: generator backend")
    n.add_argument("--model", default=None)
    n.add_argument("--prompt", default=None)
    n.add_argument("--seed", type=int, default=None)

    v = sub.add_parser("validate", help="check an already-normalized asset (non-mutating)")
    common(v)

    args = p.parse_args(argv)

    try:
        contract = load_contract(args.contract)
    except ContractError as e:
        print(f"contract error: {e}", file=sys.stderr)
        return 1
    if not Path(args.input).exists():
        print(f"input not found: {args.input}", file=sys.stderr)
        return 1
    img = Image.open(args.input)

    if args.cmd == "validate":
        res = validate(img, args.asset_class, contract)
        _print_result(res, args.json)
        return 0 if res.accepted else 2

    prov = Provenance(
        backend=args.backend, model=args.model, prompt=args.prompt, seed=args.seed,
        source_sha256=Provenance.sha256_of_file(args.input),
    )
    res = normalize(img, args.asset_class, contract, quantize=args.quantize,
                    outline=args.outline, provenance=prov)
    if res.accepted:
        out = Path(args.out) if args.out else Path(args.input).with_suffix(".gated.png")
        res.image.save(out)
        res.provenance.write_sidecar(out)
        if not args.json:
            print(f"  wrote {out} + {out.name}.prov.json")
    _print_result(res, args.json)
    return 0 if res.accepted else 2


if __name__ == "__main__":
    raise SystemExit(main())
