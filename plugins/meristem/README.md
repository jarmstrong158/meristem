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
  - `pixel-art` — the sprite construction standard (hue-shifted ramps, archetype recipes,
    render-and-judge-by-eye loop); free hand-edit via Pixelorama, no paid editor
- **MCP server** (`.mcp.json`): `meristem-spec-store` — read tools, one validated write (`set_domain`),
  `scaffold_project`, `diff_domain`, `validate_all`, and a spec-inspector UI panel (SEP-1865).

## Prerequisite (until the packages are on PyPI)

The spec-store server runs `python -m meristem_spec_store.server`, so the Meristem Python packages must
be importable in the environment Claude Code launches. From a clone of this repo:

```bash
pip install -e packages/spec-store        # jsonschema + mcp
# (asset-gate, generators, compiler, verifier are used by the CLIs — install as needed)
```

The **skills work with no install** — they orchestrate the CLIs and MCP tools. The manifest is written to
`$CLAUDE_PROJECT_DIR/meristem.manifest.json`.

## Validate

```bash
claude plugin validate plugins/meristem
```
