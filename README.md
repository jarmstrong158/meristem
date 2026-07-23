# Meristem

**An AI-assisted 2D game-creation suite where you own the output as real files on your own disk.**

Not a hosted runtime. Not a chat that writes files and hopes. A spec-driven pipeline: one
schema-validated project manifest is the single source of truth, and every downstream artifact
— sprites, tilesets, levels, gear tables, engine scenes — is a *deterministic projection* of it.

Target output is a **Godot 4 project you can open, hand-edit, and ship to Steam or itch** without
our involvement.

> **Status:** Phases 0–4 done + Phase 5 on-ramp. The **vertical slice runs and is verified**, and a
> few interview answers now scaffold a valid manifest that compiles to a running Godot project. Both
> verifier loops pass (move speed 80.0 = spec; the visual loop caught — and I fixed — an enemy standing
> on water). manifest → generators → gate → LDtk → Godot → verified. Remaining Phase 5: the MCP-Apps UI
> and Claude Code plugin packaging. See [`DECISIONS.md`](DECISIONS.md) and
> [`docs/research/00-bakeoff.md`](docs/research/00-bakeoff.md).

## Quickstart

```bash
# 1. Describe your game — the game-interview skill asks ~5 questions and scaffolds a
#    complete, valid manifest (or hand-write one; see examples/slice-01/manifest.json).
# 2. Compile the manifest into a Godot 4 project:
meristem-compile examples/slice-01/manifest.json --out build/my-game
# 3. Verify it against its spec (assertion loop + visual capture):
meristem-verify build/my-game --manifest examples/slice-01/manifest.json --godot /path/to/godot --visual
# 4. Open build/my-game in Godot 4.6 — it's a normal project you own and can ship.
```

### Install it in one move — give this to your Claude

Meristem installs itself into **Claude Code**. Paste this to your Claude (or run the three lines):

> Install the Meristem plugin from `github.com/jarmstrong158/meristem`, then set up its engine:
>
> ```
> /plugin marketplace add jarmstrong158/meristem
> /plugin install meristem@meristem
> /meristem-setup
> ```

`/plugin install` delivers the skills, commands, and the MCP config. **`/meristem-setup`** then closes
the gap that a plugin alone can't: it clones the whole suite to `~/.meristem`, builds an isolated
Python venv, `pip install`s all five packages (so the generators, the asset gate, and the compiler
work), and repoints the spec-store MCP at that venv so it actually starts. It ends with a health check;
re-run **`/meristem-doctor`** anytime, and re-run `/meristem-setup` after a plugin update.

After setup, reload MCP servers (restart Claude Code or `/mcp`) so the spec-store server picks up the
new interpreter. Full details + troubleshooting: [`docs/INSTALL.md`](docs/INSTALL.md).

> **Note:** this is a **Claude Code** experience (desktop or CLI) — it needs local Python, a local MCP,
> and plugin support. **claude.ai on the web can't run it** (no local execution); a hosted-MCP path
> would be a separate effort.

Skills (in `plugins/meristem/skills/`): **pixel-art** (build sprites to the studio standard),
**game-interview** (idea → manifest), **style-contract-author** (the visual style), **balance-reviewer**
(design sanity pass). Commands: **/meristem-setup**, **/meristem-doctor**.

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
| `plugins/meristem/` | Claude Code plugin: the judgment skills + spec-store MCP server | 5 |
| `experiments/00-bakeoff/` | The load-bearing calibration experiment | 0 |
| `docs/` | `environment.md`, `licenses.md`, `architecture.md`, `research/` | — |

## The vertical slice (definition of "it works")

One biome, one character (idle + walk), one enemy, one item, one room, one control scheme:
spec → assets → gate → LDtk → Godot → runs → passes both verifier loops. Playable, on your disk
as a normal Godot project. Breadth comes *after* the loop closes end to end.

## Sprite library (pre-made assets)

Every sprite is **config over a fixed archetype** (dec-0022) — 13 archetypes, each built to one
hue-shifted standard (3-shade ramps, top-left light, selective outline; no colour-count limit) and
gate-validated. Pick an archetype + a `build`/`kind`/`shape` + colours; a manifest entity/item just
declares `sprite: {archetype, config}`. Discover the live menu with the `list_sprite_archetypes` MCP
tool and validate a pick with `check_sprite`. Browse everything at a glance:

![sprite library](docs/reference/library.png)

*(regenerate: `python tools/contact_sheet.py` → `docs/reference/library.png`; full table in
[`docs/reference/library.md`](docs/reference/library.md))*

**Characters** — `character`, 32×32, animated (walk)

| archetype | variant axes | colour knobs |
|---|---|---|
| `humanoid` | hair_style `short·long·ponytail·spiky·bald` · hat `none·cap·wizard·helmet·crown·hood` · beard `none·short·full` · held `none` + **every weapon** `sword·dagger·greatsword·axe·spear·staff·bow·mace·wand` + `rod·flamestaff·shield·daggers` · garment `none·apron·scarf·cloak` · feet `boots·bare` · arms `normal·stone` · hair_accent `none·flora` | skin, hair, shirt, pants, hat_color, held_color, garment_color, arm_color |

The layers are combinatorial, so knight/wizard/king/dwarf/rogue/cleric are all the same base + config.

**Creatures** — `enemy`, 32×32, each animated

| archetype | builds | idle | colour |
|---|---|---|---|
| `blob` | slime · king · cube · ooze (× size s/m/l) | squash | color |
| `ghost` | ghost · wisp · specter | float | color |
| `quadruped` | dog · wolf · boar · cat | breathe | color |
| `flyer` | bat · bird · moth | wing-flap | color |
| `serpent` | cobra · snake · viper | tongue/sway | color |
| `spider` | spider · tarantula · widow | leg-twitch | color |
| `raptor` | raptor · drake · roc | head-bob | color |
| `beetle` | beetle · scorpion · mite | skitter | color |

**Items** — `item_icon`, 16×16

| archetype | kinds | colour knobs |
|---|---|---|
| `weapon` | sword · dagger · greatsword · axe · spear · staff · bow · mace · wand | blade, hilt, grip, wood, orb |
| `consumable` | flask · bottle · vial · scroll · pouch | liquid, glass, cork |
| `pickup` | coin · heart · key · gem · ring · skull · star *(coin spins)* | color |
| `projectile` | arrow · fireball · bolt · knife · shuriken | color |
| `chest` | wood · iron · gold · crystal (× open/closed) | wood, metal |

**Terrain** — `tile`, 16×16 tileable

| archetype | tiles |
|---|---|
| `tile` | grass · dirt · water · stone · sand · snow · lava · brick |

## Non-goals for v1

3D · audio generation · multiplayer · freeform mechanic codegen · unattended autonomous runs
(human-in-the-loop with checkpoints) · our own visual editor (Pixelorama and LDtk already exist, free).

## License

MIT — see [`LICENSE`](LICENSE). Bundled/driven third-party tools keep their own licenses; see
[`docs/licenses.md`](docs/licenses.md).
