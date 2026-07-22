# meristem-compiler

Deterministic **manifest → Godot 4 project**. No LLM in this path. Refuses to compile a manifest
that fails `validate_all`.

```bash
meristem-compile examples/slice-01/manifest.json --out build/slice-01
```

Produces a Godot 4.6 project that **opens and runs** (verified headless, exit 0, no script errors):

```
build/slice-01/
├── project.godot            # name, main scene, input map (from mechanics archetype), 320x180, nearest filter
├── assets/                  # generated + gated PNGs + provenance sidecars (dec-0011 backend assignment)
├── levels/
│   ├── grove_01.ldtk        # canonical, LDtk-editable level (LDtk 1.5.3, resolved Tiles + IntGrid)
│   ├── tileset.png          # composed from the terrain tiles
│   └── grove_01.grid.json   # runtime grid for the zero-addon ground builder
├── scenes/                  # player.tscn, enemy.tscn, main.tscn
└── scripts/                 # player.gd (from mechanics template), enemy.gd, world.gd
```

## How the pieces map

| Manifest | → | Godot artifact |
|---|---|---|
| `project` | → | `project.godot` (name, resolution, input map) |
| `mechanics` archetype params | → | `scripts/player.gd` (template with params substituted) |
| `entities` (sprite refs) | → | generated + gated `assets/*.png`, `scenes/{player,enemy}.tscn` |
| `world` + synthesized layout | → | `levels/grove_01.ldtk` (semantic ints → resolved tiles, dec-0014) |
| `items`, `narrative`, `economy` | → | (carried in the manifest; wired into gameplay in later phases) |

## Design decisions

- **LDtk = resolved Tiles + IntGrid, not auto-rules** (dec-0014). The compiler resolves the semantic
  grid to explicit `gridTiles` (the importer reads baked tiles anyway); the IntGrid layer keeps the
  semantics. The LLM never writes tile IDs — the deterministic compiler does.
- **The slice runs with zero addons** (dec-0015). `world.gd` builds the ground from the emitted grid
  JSON; the `.ldtk` is the canonical editable level, and `godot-ldtk-importer` is the documented
  production round-trip (to be vendored next).

## Tests

```bash
python -m pytest -q                          # 6 tests (structure, .ldtk invariants, invalid-manifest refusal)
MERISTEM_GODOT=/path/to/godot python -m pytest -q   # + engine smoke: import & run in real Godot
```
