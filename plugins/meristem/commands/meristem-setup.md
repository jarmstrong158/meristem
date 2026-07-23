---
description: Install the Meristem engine — clone the suite, build a venv, install the packages, wire up the spec-store MCP, and verify it.
argument-hint: "[--branch main] [--home ~/.meristem]"
allowed-tools: Bash(python3:*), Bash(python:*), Read
---

Bring the whole Meristem suite up on this machine by running the bundled self-installer.

The installer is standard-library-only and idempotent. It clones the suite to `~/.meristem`,
builds an isolated venv, `pip install`s all five packages (including the spec-store `[mcp]` extra),
repoints this plugin's spec-store MCP at that venv's Python, and runs a health check.

Do this:

1. Run the bootstrap, passing this plugin's root so it can repoint the MCP. The script needs
   **Python 3.10+** — prefer `python3`, and fall back to `python` if `python3` is not on PATH:

   ```
   python3 "$CLAUDE_PLUGIN_ROOT/scripts/install.py" --plugin-root "$CLAUDE_PLUGIN_ROOT" $ARGUMENTS
   ```

2. Read the installer's output — it prints each step and ends with a doctor summary.

3. **If the doctor is ALL GREEN:** tell the user setup succeeded, note that the suite lives at
   `~/.meristem` (see its `ENVIRONMENT.md`), and remind them to **reload MCP servers** — restart
   Claude Code, or run `/mcp` — so the spec-store server picks up the newly-installed interpreter.

4. **If anything FAILED:** read the FAIL/ERROR lines and fix the *root cause* before retrying —
   the usual culprits are (a) no `git` on PATH, (b) no Python 3.10+ installed, or (c) no network to
   reach GitHub. Explain what's missing, then re-run the command.

Only run the installer — do not edit any source files.
