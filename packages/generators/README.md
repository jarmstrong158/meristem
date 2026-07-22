# meristem-generators

Pluggable asset backends behind one interface:

```python
generate(spec: AssetSpec, contract) -> PIL.Image   # native-size RGBA, gate-conformant
```

The whole point of the boundary (DECISIONS dec-0009): the asset gate, compiler, and everything
downstream never know *which* backend drew a pixel. A future paid-API or CC0-LoRA diffusion backend
registers alongside these two and works everywhere without touching the gate.

## Backends (promoted from the Phase 0 bake-off, dec-0011)

| Backend | Strength | How |
|---|---|---|
| `procedural` | **surfaces** — terrain tiles/textures | algorithmic shape grammar + palette ramps + uniform bevel; deterministic, ~0-cost |
| `agent-drawn` | **objects** — character, enemy, icons, UI | hand-authored palette-index pixel art; tiles fall back to procedural |

The bake-off's blind judge rated the mixed `procedural`-tiles + `agent-drawn`-sprites set 5/5 "one
artist" (see `docs/research/00-bakeoff.md`). That mix is the intended default assignment.

## Use

```python
from meristem_generators import AssetSpec, get
from asset_gate import load_contract

contract = load_contract("style-contract.json")
img = get("agent-drawn").generate(AssetSpec("character", "player", "idle"), contract)
img.save("char_player_idle.png")   # already gate-conformant
```

`available()` lists registered backends; `register(gen)` adds one. `supports(spec)` reports whether a
backend has a recipe (procedural raises `NotImplementedError` for unknown assets rather than guessing).

## Tests

```bash
python -m pytest -q          # 37 tests: every generated asset passes the gate, deterministic
```

Requires the sibling `asset-gate` package importable (the test conftest adds it to the path).
