# meristem-asset-gate

Takes **any image + a style contract** and returns a **normalized, game-ready asset** —
or **rejects it with a specific reason**. Reject-and-report is a first-class outcome: a gate
that always says yes is not a gate.

Standalone and dependency-light (Pillow + numpy). Useful on its own, with or without the rest
of Meristem.

## Install

```bash
cd packages/asset-gate
pip install -e .          # or: pip install -e ".[dev]" for tests
```

## CLI

```bash
# normalize-or-reject, writing the asset + a provenance sidecar
asset-gate normalize sprite.png --class item_icon --contract style-contract.json --out sword.png

# check an already-normalized / hand-edited asset (non-mutating)
asset-gate validate sword.png --class item_icon --contract style-contract.json
```

Exit codes: `0` accepted, `2` rejected, `1` usage/error. Add `--json` for machine-readable output.

## Library

```python
from asset_gate import load_contract, normalize
from asset_gate.provenance import Provenance
from PIL import Image

contract = load_contract("style-contract.json")
res = normalize(Image.open("in.png"), "item_icon", contract,
                provenance=Provenance(backend="agent-drawn", seed=7))
if res.accepted:
    res.image.save("out.png")
    res.provenance.write_sidecar("out.png")   # -> out.png.prov.json
else:
    print("rejected:", res.reasons)
```

## What it does

Two asset shapes, inferred from the contract's `anchor` rule:

- **Sprites** (`center` / `bottom_center`): enforce hard alpha → quantize to the locked palette →
  trim to content → **reject if larger than the canvas** or empty → optional 1px outline →
  repivot onto the canvas per anchor.
- **Tiles** (`top_left`): validated strictly as full-bleed material — **reject** if the size is
  wrong or any pixel is transparent. Tileability is the compiler's job (TilePipe2 / LDtk auto-layers),
  not a baked-in bevel (see `DECISIONS.md` dec-0012).

Every accepted asset gets a **provenance sidecar** (`<asset>.prov.json`): backend, model+version,
prompt, seed, style-contract hash, source-image hash, gate version, timestamp, `human_edited` flag —
enough to produce an accurate Steam / itch.io AI disclosure.

## Guarantees on accepted output

- 100% of opaque pixels are exact locked-palette colors (`subset_of_palette`)
- zero semi-transparent pixels (hard alpha)
- exact canvas size for the class
- tiles are fully opaque; sprites are repivoted per the contract anchor

## Not yet implemented (Phase 1 remaining)

Collision-polygon derivation from the alpha channel, animation-tag metadata, and atlas packing with a
JSON manifest. The `generate(spec, contract) -> Image` generator backends live in `packages/generators`.

## Tests

```bash
python -m pytest -q          # 20 tests
```
