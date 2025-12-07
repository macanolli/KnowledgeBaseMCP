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
source .venv/bin/activate  

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
python server.py
```

## Docker Deployment

### Using Docker Compose (Recommended)

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

   **Note:** Remove `:ro` to allow write access if you want to create/edit notes through the MCP server.

3. **Build and run**:
   ```bash
   docker-compose up -d
   ```

4. **View logs**:
   ```bash
   docker-compose logs -f
   ```

5. **Stop the container**:
   ```bash
   docker-compose down
   ```

### Using Docker CLI

1. **Build the image**:
   ```bash
   docker build -t knowledgebase-mcp .
   ```

2. **Run the container**:
   ```bash
   docker run -d \
     --name knowledgebase-mcp \
     -v /path/to/your/notes:/data/notes \
     -v $(pwd)/data/db:/data/db \
     knowledgebase-mcp
   ```

   **Note:** Add `:ro` after `/data/notes:ro` if you want read-only access to protect your files.

3. **View logs**:
   ```bash
   docker logs -f knowledgebase-mcp
   ```

### Pulling from Docker Hub

If the image is published to Docker Hub:

```bash
docker pull macanolli/knowledgebase-mcp:latest

docker run -d \
  --name knowledgebase-mcp \
  -v /path/to/your/notes:/data/notes \
  -v $(pwd)/data/db:/data/db \
  macanolli/knowledgebase-mcp:latest
```

**Note:** Add `:ro` after `/data/notes:ro` if you want read-only access to protect your files.

### Docker Volume Notes

- **Notes directory** (`/data/notes`): Mounted with read-write access by default to enable creating/editing notes. Add `:ro` for read-only mode if you prefer to protect your original files.
- **Database directory** (`/data/db`): Persists the search index between container restarts
- Replace `/path/to/your/notes` with the absolute path to your markdown notes folder

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
