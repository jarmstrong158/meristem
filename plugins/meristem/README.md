# Meristem plugin

Install the Meristem workflow into Claude Code: the game-creation **skills** plus the **spec-store MCP
server** (schema-enforced manifest, with an inline spec-inspector panel where the host supports MCP Apps).

```
/plugin marketplace add jarmstrong158/meristem
/plugin install meristem@meristem
```

## What it bundles

- **Skills** (`skills/`, auto-discovered):
  - `game-interview` — ~5 questions → a valid strawman manifest → mutate → compile
  - `style-contract-author` — define the locked palette + visual rules
  - `balance-reviewer` — a manifest design sanity pass
  - `pixel-art` — the sprite construction standard (hue-shifted ramps, the 15-archetype registry +
    build knobs, animation, render-and-judge-by-eye loop); free hand-edit via Pixelorama, no paid editor
- **MCP server** (`.mcp.json`): `meristem-spec-store` — read tools, one validated write (`set_domain`),
  `scaffold_project`, `diff_domain`, `validate_all`, and a spec-inspector UI panel (SEP-1865). Sprites:
  - `list_sprite_archetypes` — the pickable vocabulary
  - `check_sprite` — validate one pick (errors for bad builds, warnings for config keys that do nothing)
  - `preview_sprite` — **render** one sprite to a PNG you can look at, against the manifest's own style
    contract, with the gate verdict beside it
  - `compare_builds` — render every variant of an archetype as labelled silhouettes, to check they
    actually read as different things

The full sprite vocabulary is browsable at `docs/reference/library.png` (`python tools/contact_sheet.py`).

## Prerequisite (until the packages are on PyPI)

The spec-store server runs `python -m meristem_spec_store.server`, so the Meristem Python packages must
be importable in the environment Claude Code launches. `/meristem-setup` does this for you.

To do it by hand from a clone: install the engine packages **in one command**. spec-store depends on
`meristem-generators` (sprite/tile vocabulary for cross-reference validation) and `meristem-asset-gate`
(the style contract, for rendering previews), and neither is on PyPI — so installing spec-store alone
cannot resolve them.

```bash
pip install -e packages/generators -e packages/asset-gate -e "packages/spec-store[mcp]" -e packages/compiler -e packages/verifier
```

The **skills work with no install** — they orchestrate the CLIs and MCP tools. The manifest is written to
`$CLAUDE_PROJECT_DIR/meristem.manifest.json`.

## Validate

```bash
claude plugin validate plugins/meristem
```
