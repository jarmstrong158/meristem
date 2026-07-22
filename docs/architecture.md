# Architecture

*Status: v0, Phase 0. This grows as phases land. Decisions live in [`../DECISIONS.md`](../DECISIONS.md).*

## The one idea

A single **schema-validated manifest** is the source of truth. Everything else is a **deterministic
projection** of it. No artifact is authored twice; nothing downstream is canonical. Regenerating from
the manifest reproduces the project (modulo user hand-edits, which are honored — see Phase 3).

```
                 ┌─────────────────────────────────────────────┐
                 │      spec-store (MCP, Phase 2)               │
                 │   manifest.json  — schema-enforced writes    │
                 │   project · style-contract · narrative ·     │
                 │   entities · items · mechanics · economy ·   │
                 │   world                                      │
                 └───────────────┬─────────────────────────────┘
                                 │ (validated read)
          ┌──────────────────────┼──────────────────────────┐
          ▼                      ▼                           ▼
  generators (P1)          compiler (P3)              verifier (P4)
  generate(spec,           spec → LDtk (.ldtk,        headless assertions
    contract) -> Image     IntGrid + rules) +         + offscreen visual
          │                Godot .tscn/.tres          critique
          ▼                from templates
  asset gate (P1)                 │
  normalize-or-reject             ▼
  + provenance sidecar     Godot 4 project on disk (user-owned, hand-editable)
```

## Layer contracts

**Generators (Phase 1).** One interface: `generate(spec, style_contract) -> Image`. Backends are
interchangeable and know nothing about the gate. v1 backends: **procedural** (deterministic shape
grammar + palette ramps) and **agent-drawn** (Claude drawing against a Pillow canvas with a visual
feedback loop). Diffusion is cut for v1 (DECISIONS dec-0002); the boundary lets it or a paid API
be added later without touching anything downstream.

**Asset gate (Phase 1).** Takes any image + a style contract, returns a normalized game-ready asset
*or a specific rejection reason*. Operations: palette quantization to the locked palette, grid snap +
integer scale, hard-alpha enforcement, trim-to-content + repivot, outline policy, alpha→collision
polygon, atlas packing, naming. **Reject-and-report is a first-class outcome** — a gate that always
says yes is not a gate. Every accepted asset gets a provenance sidecar.

**Spec store (Phase 2).** Stateful MCP server. Writes that fail schema validation are **rejected, not
coerced**. Cross-references enforced (an item dropping from a nonexistent enemy is an error). Tools:
validated reads, validated writes, diff, `validate_all`. No raw write-anything tool. Mechanics are
**parameters over a fixed archetype library** (platformer / top-down / turn-based), never freeform code.

**Compiler (Phase 3).** Deterministic, no LLM. Spec world graph → LDtk (model writes semantic
integers, LDtk rules paint tiles — DECISIONS dec-0008). Entities/items → `.tres`/JSON. Mechanics
params → Godot scenes/scripts from templates. Idempotent; never clobbers hand-edits (user-owned
regions honored). Emits text formats (`.tscn`/`.tres`) so everything is diffable.

**Verifier (Phase 4).** Two loops, both free. **Assertion loop** — derive checkable assertions from
the spec (120 px/s move speed, 3-tile jump apex) and test headlessly via state injection under true
`--headless`. **Visual loop** — run with an offscreen render context, capture PNGs, critique against
the spec with vision (missing textures, z-order, off-palette, unreadable silhouettes). Windows note:
no Xvfb, no `--headless` screenshots — offscreen viewport capture instead (DECISIONS dec-0007). Gate
on both; a clean compile is not evidence.

**UI + distribution (Phase 5).** UI via MCP Apps (SEP-1865) — inline panels, no Electron/web/auth.
Distribution as a Claude Code plugin with a git-repo marketplace. Skills (judgment, no new verbs):
the game interview (~5 questions → strawman spec → mutate), style-contract author, balance reviewer.

## What is deliberately *not* here

No hosted state. No account. No network in the default path. No LLM in the compiler. No freeform
mechanic codegen. No fourth abstraction layer without stopping to ask.
