# Semantica — Cline Plugin

Adds all 17 Semantica skills, 3 agents, and hook configuration to Cline (VS Code extension).

## MCP Server Setup (recommended)

In Cline settings, add a new MCP server:

```json
{
  "semantica": {
    "command": "python",
    "args": ["-m", "semantica.mcp_server"],
    "env": {}
  }
}
```

Cline will discover all 12 Semantica tools automatically on connection.

## Requirements

- Python 3.8+
- `pip install semantica`
