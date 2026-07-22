# meristem-spec-store

The **single source of truth**: a versioned, schema-enforced project manifest. Everything
downstream (assets, LDtk levels, Godot scenes) is a deterministic projection of it.

Writes that fail validation are **rejected, not coerced**. Cross-references are enforced across
domains — an item that drops from an enemy that doesn't exist is a valid `items` object but an
invalid *manifest*, and `validate_all` catches it.

## Domains (schemas in `../../schemas`)

`project` · `style_contract` · `narrative` · `entities` · `items` · `mechanics` · `economy` · `world`

**Mechanics are parameters over a fixed archetype library** — never freeform code. The three
archetypes (`platformer_controller`, `top_down_controller`, `turn_based_combat`) each have a typed,
schema-checked parameter set.

## Library

```python
from meristem_spec_store import SpecStore, SpecValidationError

store = SpecStore()
store.set_domain("mechanics", {"archetypes": [
    {"id": "hero", "kind": "platformer_controller",
     "params": {"move_speed": 120, "accel": 800, "jump_height": 48, "gravity": 900}}
]})
try:
    store.set_domain("project", {"camera": "vr", ...})   # rejected
except SpecValidationError as e:
    print(e.errors)

report = store.validate_all()      # per-domain schemas + cross-references
store.save("meristem.manifest.json")
```

## MCP server

```bash
pip install -e ".[mcp]"
MERISTEM_MANIFEST=./my.manifest.json python -m meristem_spec_store.server
```

Tools exposed:

| Tool | Kind | Notes |
|---|---|---|
| `list_domains` / `get_domain` / `get_manifest` | read | |
| `set_domain(domain, value, actor, reason)` | **validated write** | the *only* mutation; schema-enforced, rejected not coerced |
| `scaffold_project(title, genre, control, …)` | scaffold | fill all 8 domains with a valid strawman (the game-interview on-ramp) |
| `diff_domain(domain, candidate)` | diff | preview a change |
| `validate_all()` | validate | per-domain schemas + cross-references |
| `inspect_manifest()` | UI panel | renders an inline spec-inspector (MCP Apps / SEP-1865); returns the same data as structured content for hosts without panel support |

There is **no raw write-anything tool** — you set a whole domain and it is validated against that
domain's schema before it is accepted. Every accepted mutation is recorded in history with provenance.

## Tests

```bash
python -m pytest -q          # 17 tests
```
