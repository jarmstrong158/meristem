# Installing Meristem

Meristem is a **Claude Code** experience: it needs local Python, a local MCP server, and plugin
support. The share unit is this public repo — the "link" you give someone is
`github.com/jarmstrong158/meristem`.

## Give this to your Claude

```
/plugin marketplace add jarmstrong158/meristem
/plugin install meristem@meristem
/meristem-setup
```

That's the whole install. What each line does:

| Step | What it delivers |
|------|------------------|
| `/plugin marketplace add …` | Registers this repo as a plugin marketplace. |
| `/plugin install meristem@meristem` | Installs the **skills** (pixel-art, game-interview, style-contract-author, balance-reviewer), the **commands** (/meristem-setup, /meristem-doctor), and the **spec-store MCP** config. |
| `/meristem-setup` | Installs the **engine** — see below. |

## Why `/meristem-setup` is needed

A Claude Code plugin ships only what's under `plugins/meristem/` (skills, commands, MCP config). The
actual engine — the five `meristem_*` Python packages, the generators, `tools/`, and the example
project — lives at the repo root and is **not** carried by the plugin. Without installing it, the
spec-store MCP (`python -m meristem_spec_store.server`) and the pixel-art skill (`sprite_catalog()`,
the asset gate) fail with `ModuleNotFoundError`.

`/meristem-setup` runs [`plugins/meristem/scripts/install.py`](../plugins/meristem/scripts/install.py),
a standard-library-only, idempotent bootstrap that:

1. finds a **Python 3.10+** to build with;
2. **clones the whole suite** to `~/.meristem` (so you get the generators, tools, and examples on
   disk — you own the files, per Meristem's ethos);
3. creates an isolated **venv** at `~/.meristem/.venv` and `pip install`s all five packages editable,
   including the spec-store `[mcp]` extra;
4. **repoints** the installed plugin's `.mcp.json` at that venv's Python, so the MCP can import its deps;
5. writes `~/.meristem/ENVIRONMENT.md` (the paths the skills/tools should use);
6. runs a **doctor** — import checks plus a live `sprite_catalog()` smoke test.

After it finishes, **reload MCP servers** (restart Claude Code, or `/mcp`) so the spec-store server
starts under the new interpreter.

## Prerequisites

- **Claude Code** (desktop or CLI).
- **git** on `PATH`.
- **Python 3.10+** on `PATH` (`python3` or `python`). Get it from <https://www.python.org/downloads/>.
- **Godot 4.6** — only needed to open/run a compiled project, not to install Meristem.

## Health check & re-install

- `/meristem-doctor` — re-runs the health check anytime.
- `/meristem-setup` — idempotent; re-run it after a plugin update (a plugin update overwrites the
  repointed `.mcp.json`, and re-running setup fixes it and pulls the latest suite).

Options pass straight through, e.g. a different location or branch:

```
/meristem-setup --home ~/tools/meristem --branch main
```

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `git is required but was not found` | Install git, reopen the terminal, re-run `/meristem-setup`. |
| `need Python 3.10+ but none was found` | Install Python 3.10+ and ensure `python3`/`python` is on `PATH`. |
| spec-store MCP shows **failed** after setup | Reload MCP (restart Claude Code or `/mcp`) — it must re-read the repointed `.mcp.json`. |
| doctor `FAIL import mcp dep` | Re-run `/meristem-setup`; the `[mcp]` extra installs `mcp>=1.0` into the venv. |
| `~/.meristem exists and is not a git checkout` | Move that folder aside (or pass `--home <other>`), then re-run. |

## The web question

claude.ai on the web cannot run this — there's no local Python or plugin host. Making Meristem usable
from the web would mean standing up a **hosted** spec-store MCP (a remote connector) and a
cloud-side generator/gate service; that's a separate, larger effort, tracked as a non-goal for now.
