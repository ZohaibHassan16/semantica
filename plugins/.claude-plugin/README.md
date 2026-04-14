# Semantica Plugins (Community Guide)

Semantica ships a shared plugin bundle under `plugins/` with skills, agents, and hooks for knowledge graphs, context graphs, decision intelligence, reasoning, explainability, provenance, ontology, and export workflows.

This README covers installation across every supported platform.

## Supported Platforms

| Platform | Method | Config file |
|---|---|---|
| Claude Code | Native plugin bundle | `plugins/.claude-plugin/plugin.json` |
| Cursor | Native plugin bundle | `plugins/.cursor-plugin/plugin.json` |
| Codex CLI | Native plugin bundle | `plugins/.codex-plugin/plugin.json` |
| Windsurf | MCP server + plugin bundle | `plugins/.windsurf-plugin/plugin.json` |
| Cline (VS Code) | MCP server + plugin bundle | `plugins/.cline-plugin/plugin.json` |
| Continue | MCP server | `plugins/.continue-plugin/plugin.json` |
| VS Code | MCP server | `plugins/.vscode-plugin/plugin.json` |
| Claude Desktop | MCP server | — (see MCP section below) |
| Any MCP client | MCP server | `python -m semantica.mcp_server` |

## Prerequisites

1. Clone the repository:

```bash
git clone https://github.com/Hawksight-AI/semantica.git
cd semantica
```

2. Ensure the plugin bundle exists at:

```text
plugins/
  skills/          ← 17 domain skills
  agents/          ← 3 specialized agents
  hooks/           ← hooks.json
  .claude-plugin/  ← Claude Code manifest
  .cursor-plugin/  ← Cursor manifest
  .codex-plugin/   ← Codex CLI manifest
  .windsurf-plugin/← Windsurf manifest + MCP config
  .cline-plugin/   ← Cline manifest + MCP config
  .continue-plugin/← Continue manifest + MCP config
  .vscode-plugin/  ← VS Code manifest + MCP config
```

## Plugin Contents

- `skills/`: 17 domain skills (`causal`, `decision`, `explain`, `reason`, `temporal`, etc.)
- `agents/`: specialized agents (`decision-advisor`, `explainability`, `kg-assistant`)
- `hooks/hooks.json`: plugin hook configuration
- `.claude-plugin/plugin.json`: Claude manifest
- `.cursor-plugin/plugin.json`: Cursor manifest
- `.codex-plugin/plugin.json`: Codex manifest
- `*/marketplace.json`: local marketplace definitions

## Install and Use in Claude Code

### Local install (fastest)

From the repository root:

```bash
claude --plugin-dir ./plugins
```

If your Claude setup uses plugin commands in-session, use:

```bash
/plugin install ./plugins
```

### Install from a GitHub marketplace

Add a marketplace hosted in git:

```bash
/plugin marketplace add <owner>/semantica
```

Install Semantica from that marketplace:

```bash
/plugin install semantica@<marketplace-name>
```

### Verify in Claude

Run one of these in chat:

```text
/semantica:decision list
/semantica:explain decision <decision_id>
```

If the plugin is installed correctly, Claude should recognize the `/semantica:*` skills.

## Install and Use in Codex

1. Ensure your repo marketplace exists at `.agents/plugins/marketplace.json`.
2. Point the plugin entry `source.path` to `./plugins` (or your chosen plugin directory).
3. Restart Codex and install from the marketplace UI.

Codex manifest used by this bundle:

- `.codex-plugin/plugin.json`

### Verify in Codex

After install, run a Semantica skill command in chat, for example:

```text
/semantica:causal chain --subject <decision_id> --depth 3
```

## Install and Use in Cursor

Cursor reads plugin metadata from:

- `.cursor-plugin/plugin.json`
- `.cursor-plugin/marketplace.json`

If you maintain a team/community plugin repo, publish this `plugins/` directory and refresh/reinstall in Cursor Marketplace to pick up updates.

### Verify in Cursor

Try one of these commands:

```text
/semantica:reason deductive "IF Person(x) THEN Mortal(x)"
/semantica:visualize topology
```

## First Commands to Try

After installing on any platform, these are good smoke tests:

1. `/semantica:decision record <category> "<scenario>" "<reasoning>" <outcome> <confidence>`
2. `/semantica:decision list`
3. `/semantica:causal chain --subject <decision_id> --depth 3`
4. `/semantica:explain decision <decision_id>`
5. `/semantica:validate graph`

## MCP Server (Windsurf · Cline · Continue · VS Code · Claude Desktop · Any tool)

Semantica includes a full MCP server (`semantica/mcp_server.py`) that exposes 12 tools and 3 resources over stdio — compatible with any MCP-aware tool.

### Start the server

```bash
python -m semantica.mcp_server
```

### Configure in your tool

**Claude Desktop** — `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "semantica": {
      "command": "python",
      "args": ["-m", "semantica.mcp_server"]
    }
  }
}
```

**Windsurf** — `~/.codeium/windsurf/mcp_config.json`:

```json
{
  "mcpServers": {
    "semantica": {
      "command": "python",
      "args": ["-m", "semantica.mcp_server"]
    }
  }
}
```

**Cline** — Cline MCP settings panel → Add server:

```json
{
  "semantica": {
    "command": "python",
    "args": ["-m", "semantica.mcp_server"]
  }
}
```

**Continue** — `~/.continue/config.json`:

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

**VS Code** — `settings.json`:

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

### Available MCP tools

| Tool | Description |
|---|---|
| `extract_entities` | Named entity recognition from text |
| `extract_relations` | Relation and triplet extraction from text |
| `record_decision` | Record a decision with full context and metadata |
| `query_decisions` | Query recorded decisions by natural language or category |
| `find_precedents` | Find past decisions similar to a scenario |
| `get_causal_chain` | Trace upstream/downstream causal chain from a decision |
| `add_entity` | Add a node/entity to the knowledge graph |
| `add_relationship` | Add a directed edge between two entities |
| `run_reasoning` | Run IF/THEN rules over facts to derive new facts |
| `get_graph_analytics` | PageRank centrality and community detection |
| `export_graph` | Export graph as Turtle, JSON-LD, N-Triples, or JSON |
| `get_graph_summary` | Node count, decision count, graph status |

### Available MCP resources

| URI | Description |
|---|---|
| `semantica://graph/summary` | High-level graph statistics |
| `semantica://decisions/list` | All recorded decisions |
| `semantica://schema/info` | Server info and capability list |

### Environment variables

| Variable | Description |
|---|---|
| `SEMANTICA_KG_PATH` | Path to a persisted graph to load on start |
| `SEMANTICA_LOG_LEVEL` | Log level: DEBUG, INFO, WARNING (default: WARNING) |

## Community Notes

- Keep plugin name/version/keywords updated in each manifest before publishing.
- Keep skill frontmatter consistent (`name` + `description`) for reliable discovery.
- For open-source sharing, include this folder as-is so skills, agents, and hooks remain bundled.
