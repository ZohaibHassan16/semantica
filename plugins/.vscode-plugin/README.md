# Semantica — VS Code Plugin

Adds Semantica as an MCP server to VS Code (via GitHub Copilot Chat or any MCP-aware extension).

## MCP Server Setup

Add to your VS Code `settings.json`:

```json
{
  "github.copilot.chat.mcp.servers": {
    "semantica": {
      "command": "python",
      "args": ["-m", "semantica.mcp_server"]
    }
  }
}
```

Or if using the VS Code MCP extension directly:

```json
{
  "mcp.servers": {
    "semantica": {
      "command": "python",
      "args": ["-m", "semantica.mcp_server"]
    }
  }
}
```

## Requirements

- Python 3.8+
- `pip install semantica`
