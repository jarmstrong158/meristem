---
description: Check the Meristem engine install — imports, live sprite catalog, and MCP readiness.
allowed-tools: Bash(python3:*), Bash(python:*)
---

Run the Meristem health check and report the result.

Run (prefer `python3`, fall back to `python`):

```
python3 "$CLAUDE_PLUGIN_ROOT/scripts/install.py" --doctor
```

Summarize the PASS/FAIL lines for the user. If every check passes, say the engine is healthy and
the spec-store MCP can start (reload MCP with `/mcp` if it still shows as failed). If anything fails,
tell the user to run `/meristem-setup` to (re)install the engine.
