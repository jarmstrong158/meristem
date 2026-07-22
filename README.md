# Meristem

**An AI-assisted 2D game-creation suite where you own the output as real files on your own disk.**

Not a hosted runtime. Not a chat that writes files and hopes. A spec-driven pipeline: one
schema-validated project manifest is the single source of truth, and every downstream artifact
— sprites, tilesets, levels, gear tables, engine scenes — is a *deterministic projection* of it.

Target output is a **Godot 4 project you can open, hand-edit, and ship to Steam or itch** without
our involvement.

> **Status:** Phases 0–3 done — the **vertical slice runs**. A hand-written manifest compiles to a
> Godot 4.6 project that opens and runs headless (exit 0, no script errors): manifest → generators →
> gate → LDtk → Godot. Phases 4 (verifier) and 5 (UI/distribution) remain. See
> [`DECISIONS.md`](DECISIONS.md) and [`docs/research/00-bakeoff.md`](docs/research/00-bakeoff.md).

## Principles (hard constraints)

1. **Everything free.** No paid software or APIs in the critical path. Paid backends may exist only
   as optional, flagged plugins. Default path costs nothing beyond your own compute + Claude subscription.
2. **2D only.** No 3D, no audio synthesis, no multiplayer in v1.
3. **You own everything.** MIT code. No telemetry, no account, no cloud dependency in the default path.
4. **Provenance is tracked.** Every generated asset carries a sidecar (backend, model+version, prompt,
   seed, style-contract hash, timestamp, human-edited flag) so you can file accurate Steam/itch AI disclosures.

## The pipeline

```
style contract + spec manifest   (Phase 2, schema-enforced, single source of truth)
        │
        ├─ generators ──► asset gate ──► normalized, provenance-tagged assets   (Phase 1)
        │   procedural / agent-drawn      palette-locked, grid-snapped, hard-alpha
        │
        └─ compiler ────► LDtk project + Godot scenes/resources                 (Phase 3)
                          model writes semantic ints; LDtk rules paint tiles
        │
        verifier ───────► headless assertions + offscreen visual critique       (Phase 4)
```

## Repo map

| Path | What | Phase |
|---|---|---|
| `schemas/` | JSON Schema per manifest domain | 2 |
| `packages/asset-gate/` | Python lib + CLI: normalize-or-reject any image to a style contract | 1 |
| `packages/generators/` | Pluggable backends behind `generate(spec, contract) -> Image` | 1 |
| `packages/spec-store/` | Stateful MCP server holding the schema-enforced manifest | 2 |
| `packages/compiler/` | Deterministic spec → LDtk + Godot project (no LLM in path) | 3 |
| `packages/verifier/` | Headless run: assertion loop + offscreen visual loop | 4 |
| `skills/` | Judgment skills: game interview, style-contract author, balance reviewer | 5 |
| `experiments/00-bakeoff/` | The load-bearing calibration experiment | 0 |
| `docs/` | `environment.md`, `licenses.md`, `architecture.md`, `research/` | — |

## The vertical slice (definition of "it works")

One biome, one character (idle + walk), one enemy, one item, one room, one control scheme:
spec → assets → gate → LDtk → Godot → runs → passes both verifier loops. Playable, on your disk
as a normal Godot project. Breadth comes *after* the loop closes end to end.

## Non-goals for v1

3D · audio generation · multiplayer · freeform mechanic codegen · unattended autonomous runs
(human-in-the-loop with checkpoints) · our own visual editor (Pixelorama and LDtk already exist, free).

## License

MIT — see [`LICENSE`](LICENSE). Bundled/driven third-party tools keep their own licenses; see
[`docs/licenses.md`](docs/licenses.md).
