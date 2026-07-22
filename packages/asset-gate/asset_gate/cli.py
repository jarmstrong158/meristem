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


def _cmd_collision(args) -> int:
    from .collision import alpha_to_polygon
    if not Path(args.input).exists():
        print(f"input not found: {args.input}", file=sys.stderr)
        return 1
    poly = alpha_to_polygon(Image.open(args.input), tolerance=args.tolerance)
    payload = {"input": args.input, "tolerance": args.tolerance, "vertices": poly}
    if args.out:
        Path(args.out).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    if args.json:
        print(json.dumps(payload))
    else:
        print(f"{len(poly)} vertices: {poly}")
    return 0 if poly else 2


def _cmd_atlas(args) -> int:
    from .atlas import pack
    entries = []
    for pth in args.inputs:
        if not Path(pth).exists():
            print(f"input not found: {pth}", file=sys.stderr)
            return 1
        entries.append((Path(pth).stem, Image.open(pth)))
    atlas = pack(entries, max_width=args.max_width, padding=args.padding)
    ip, mp = atlas.save(args.out, args.manifest)
    print(f"packed {len(entries)} frames -> {ip} ({atlas.image.size[0]}x{atlas.image.size[1]}) + {mp}")
    return 0


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

    col = sub.add_parser("collision", help="derive a collision polygon from the alpha channel")
    col.add_argument("input")
    col.add_argument("--tolerance", type=float, default=1.0)
    col.add_argument("--out", help="write polygon JSON here")
    col.add_argument("--json", action="store_true")

    at = sub.add_parser("atlas", help="pack images into a sheet + JSON manifest")
    at.add_argument("inputs", nargs="+")
    at.add_argument("--out", required=True, help="output sheet PNG")
    at.add_argument("--manifest", help="output manifest JSON (default: <out>.json)")
    at.add_argument("--max-width", type=int, default=256)
    at.add_argument("--padding", type=int, default=0)

    args = p.parse_args(argv)

    if args.cmd == "collision":
        return _cmd_collision(args)
    if args.cmd == "atlas":
        return _cmd_atlas(args)

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
