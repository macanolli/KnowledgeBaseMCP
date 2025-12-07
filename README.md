# Knowledge Base MCP Server

A Model Context Protocol (MCP) server for managing and searching personal markdown notes. This repository demonstrates the basic structure for implementing MCP.

## Features

- 📝 **Create, update, and append** to markdown notes
- 🔍 **Full-text search** with snippet highlighting (SQLite FTS5)
- 🏷️ **YAML frontmatter** support for tags and metadata
- 📊 **Statistics** and recently modified notes
- 🔄 **Auto-indexing** on startup

## Quick Start

### Prerequisites

- Python 3.10+
- [FastMCP](https://github.com/jlowin/fastmcp)

### Installation

```bash
# Clone the repository
git clone https://github.com/macanolli/KnowledgeBaseMCP.git
cd KnowledgeBaseMCP

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Create a `.env` file:

```bash
KB_DIR=/path/to/your/notes
KB_DB=/path/to/database/kb_index.db
```

### Run

```bash
python kb_server.py
```

## Connect to Claude Desktop

### Config File Locations

- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux:** `~/.config/Claude/claude_desktop_config.json`

### Configuration

Add to your config file:

```json
{
  "mcpServers": {
    "knowledge-base": {
      "command": "/path/to/.venv/bin/python",
      "args": ["/path/to/kb_server.py"]
    }
  }
}
```

**Windows example:**
```json
{
  "mcpServers": {
    "knowledge-base": {
      "command": "C:\\Users\\YourName\\KnowledgeBaseMCP\\.venv\\Scripts\\python.exe",
      "args": ["C:\\Users\\YourName\\KnowledgeBaseMCP\\kb_server.py"]
    }
  }
}
```

Restart Claude Desktop after saving.

## Connect to VS Code (Cline)

### Install Cline Extension

1. Open VS Code
2. Go to Extensions (Ctrl+Shift+X / Cmd+Shift+X)
3. Search for "Cline"
4. Install the extension

### Config File Location

- **Windows:** `%APPDATA%\Code\User\globalStorage\saoudrizwan.claude-dev\settings\cline_mcp_settings.json`
- **macOS:** `~/Library/Application Support/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`
- **Linux:** `~/.config/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`

### Configuration

Add to the config file:

```json
{
  "mcpServers": {
    "knowledge-base": {
      "command": "/path/to/.venv/bin/python",
      "args": ["/path/to/kb_server.py"]
    }
  }
}
```

**Windows example:**
```json
{
  "mcpServers": {
    "knowledge-base": {
      "command": "C:\\Users\\YourName\\KnowledgeBaseMCP\\.venv\\Scripts\\python.exe",
      "args": ["C:\\Users\\YourName\\KnowledgeBaseMCP\\kb_server.py"]
    }
  }
}
```

Restart VS Code after saving.

## Available Tools

| Tool | Description |
|------|-------------|
| `search_notes` | Full-text search through notes |
| `read_note` | Read complete note contents |
| `list_recent_notes` | Show recently modified notes |
| `create_note` | Create new note with tags |
| `update_note` | Replace note content |
| `append_to_note` | Add to existing note |
| `reindex_kb` | Refresh search index |
| `get_kb_stats` | View statistics |

## Usage Examples

Once connected to Claude or Cline:

```
"Search my notes for Python async"
"Create a note about Docker networking"
"Show my recent notes"
"Add these instructions to my knowledge base"
```

## Project Structure

```
KnowledgeBaseMCP/
├── server.py          # Main MCP server entry point
├── database.py        # SQLite operations
├── tools.py           # MCP tool implementations
├── .env               # Configuration (create this)
└── requirements.txt   # Python dependencies
```

## How It Works

1. **Indexes** markdown files from `KB_DIR` into SQLite
2. **Parses** YAML frontmatter for metadata
3. **FTS5 search** enables fast full-text queries
4. **Auto-reindexing** when creating/updating notes via MCP tools

## License

MIT

## Contributing

Pull requests welcome! Please ensure your code follows the existing structure:
- Database operations in `database.py`
- Tool implementations in `tools.py`  
- MCP decorators in `server.py`
