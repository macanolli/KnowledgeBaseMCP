# Knowledge Base MCP Server

A Model Context Protocol (MCP) server for managing and searching personal markdown notes. 

## Features

- 📝 **Create, update, and append** to markdown notes
- 🔍 **Full-text search** with snippet highlighting (SQLite FTS5)
- 🏷️ **YAML frontmatter** support for tags and metadata
- 📊 **Statistics** and recently modified notes
- 🔄 **Auto-indexing** on startup
- 🔀 **Automatic Git sync** - Auto-commit and push changes to your repository
- 🌐 **Multiple transport modes** - STDIO (local) or SSE (HTTP server)



## Docker Deployment (Recommended)

#### Using Docker Compose

1. **Clone the repository** (if you haven't already):
   ```bash
   git clone https://github.com/macanolli/KnowledgeBaseMCP.git
   cd KnowledgeBaseMCP
   ```

2. **Create a `.env` file** to set your notes directory:
   ```bash
   KB_DIR=/path/to/your/notes
   KB_DB=/data/db/kb_index.db

   # Optional: Enable automatic git sync
   GIT_TOKEN=your_github_personal_access_token

   # Optional: Use SSE transport instead of STDIO
   MCP_TRANSPORT=stdio  # or 'sse' for HTTP server
   PORT=3399
   HOST=0.0.0.0
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

Create a `.env` file (or copy from `.env.example`):

```bash
KB_DIR=/path/to/your/notes
KB_DB=/path/to/database/kb_index.db

# Optional: Enable automatic git sync
GIT_TOKEN=your_github_personal_access_token

# Optional: Transport mode
MCP_TRANSPORT=stdio  # or 'sse' for HTTP server
PORT=3399
HOST=0.0.0.0
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
5. **Git automation** (optional) commits and pushes changes after note operations

## Advanced Configuration

### Automatic Git Sync

If your notes directory is a git repository, the server can automatically commit and push changes when notes are created, updated, or appended.

**Setup:**

1. Initialize your notes directory as a git repository:
   ```bash
   cd /path/to/your/notes
   git init
   git remote add origin https://github.com/yourusername/your-notes-repo.git
   ```

2. Create a GitHub Personal Access Token:
   - Go to: https://github.com/settings/tokens
   - Click "Generate new token (classic)"
   - Select scope: **repo** (Full control of private repositories)
   - Copy the token

3. Add the token to your `.env` file:
   ```bash
   GIT_TOKEN=ghp_your_token_here
   ```

4. Restart the server

**What happens:**
- When you create a note → automatic commit: `"Created note: title"`
- When you update a note → automatic commit: `"Updated note: filename"`
- When you append to a note → automatic commit: `"Appended to note: filename"`
- Each operation automatically pulls with rebase and pushes to your remote

### Transport Modes

**STDIO Mode (Default):**
- Local communication via standard input/output
- Used with Claude Desktop and local MCP clients
- Configure in `.env`: `MCP_TRANSPORT=stdio`

**SSE Mode (HTTP Server):**
- Server-Sent Events over HTTP
- Enables remote access to your knowledge base
- Configure in `.env`:
  ```bash
  MCP_TRANSPORT=sse
  PORT=3399
  HOST=0.0.0.0  # or specific IP
  ```
- Access at: `http://your-server:3399`

## License

MIT

## Contributing

Pull requests welcome! Please ensure your code follows the existing structure:
- Database operations in `database.py`
- Tool implementations in `tools.py`  
- MCP decorators in `server.py`
