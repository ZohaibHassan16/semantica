# Semantica — Continue Plugin

Adds Semantica as an MCP server and context provider to [Continue.dev](https://continue.dev).

## MCP Server Setup

Add to `~/.continue/config.json`:

```json
{
  "mcpServers": [
    {
      "name": "semantica",
      "command": "python",
      "args": ["-m", "semantica.mcp_server"]
    }
  ]
}
```

Continue will show all Semantica tools in the `@semantica` context provider dropdown.

## Requirements

- Python 3.8+
- `pip install semantica`
