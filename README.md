# Knowledge Base MCP Server

A Model Context Protocol (MCP) server for managing and searching personal markdown notes. 

## Features

- 📝 **Create, update, and append** to markdown notes
- 🔍 **Full-text search** with snippet highlighting (SQLite FTS5)
- 🏷️ **YAML frontmatter** support for tags and metadata
- 📊 **Statistics** and recently modified notes
- 🔄 **Auto-indexing** on startup



## Docker Deployment (Recommended)

#### Using Docker Compose

1. **Clone the repository** (if you haven't already):
   ```bash
   git clone https://github.com/macanolli/KnowledgeBaseMCP.git
   cd KnowledgeBaseMCP
   ```

2. **Edit `docker-compose.yml`** to point to your notes directory:
   ```yaml
   volumes:
     - /path/to/your/notes:/data/notes
     - ./data/db:/data/db
   ```


3. **Build and run**:
   ```bash
   docker-compose up -d
   ```


#### Docker Volume Notes

- **Notes directory** (`/data/notes`): Mounted with read-write access by default to enable creating/editing notes. Add `:ro` for read-only mode if you prefer to protect your original files.
- **Database directory** (`/data/db`): Persists the search index between container restarts
- Replace `/path/to/your/notes` with the absolute path to your markdown notes folder


## Python Virtual Environment

#### Prerequisites

- Python 3.10+
- [FastMCP](https://github.com/jlowin/fastmcp)

#### Installation

```bash
# Clone the repository
git clone https://github.com/macanolli/KnowledgeBaseMCP.git
cd KnowledgeBaseMCP

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

#### Configuration

Create a `.env` file:

```bash
KB_DIR=/path/to/your/notes
KB_DB=/path/to/database/kb_index.db
```

#### Run

```bash
python server.py
```

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
