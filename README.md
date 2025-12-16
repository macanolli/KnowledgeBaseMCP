
# Knowledge Base MCP Server

The **Knowledge Base MCP Server** is a Model Context Protocol (MCP) server designed for managing, indexing, and searching personal Markdown notes. It provides fast full-text search, structured metadata support, and optional Git-based synchronization, making it ideal for personal knowledge bases and MCP-enabled clients.

---

## Features

* 📝 **Create, update, and append** Markdown notes
* 🔍 **Full-text search** with snippet highlighting (SQLite FTS5)
* 🏷️ **YAML frontmatter** support for tags and metadata
* 📊 **Knowledge base statistics** and recently modified notes
* 🔄 **Automatic indexing** on startup and after updates
* 🔀 **Git synchronization (optional)** — auto-commit and push changes
* 🌐 **Multiple transport modes** — STDIO (local) or SSE (HTTP server)

---

## Deployment Options

You can run the server using Docker (recommended) or directly in a Python virtual environment.

---

## Docker Deployment (Recommended)

### Using Docker Compose

1. **Clone the repository**

   ```bash
   git clone https://github.com/macanolli/KnowledgeBaseMCP.git
   cd KnowledgeBaseMCP
   ```

2. **Create a `.env` file** to configure your environment:

   ```bash
   cp .env.example .env
   ```

   Edit `.env`:

   ```bash
   KB_DIR=/path/to/your/notes
   KB_DB=/data/db/kb_index.db

   # Optional: Enable automatic Git sync
   GIT_TOKEN=your_github_personal_access_token

   # Optional: Transport mode
   MCP_TRANSPORT=stdio  # or 'sse' for HTTP server
   PORT=3399
   HOST=0.0.0.0
   ```

3. **Configure Git authoring details** (required if Git sync is enabled):

   ```bash
   cp .gitconfig-docker.example .gitconfig-docker
   ```

   Edit `.gitconfig-docker`:

   ```ini
   [user]
     name = Your Name
     email = your.email@example.com
   ```

   This file is mounted into the container and used when committing note changes.

4. **Build and start the container**

   ```bash
   docker-compose up -d
   ```

---

### Docker Volume Notes

* **Notes directory (`/data/notes`)**
  Mounted with read-write access by default. Use `:ro` if you want read-only access.

* **Database directory (`/data/db`)**
  Persists the search index across container restarts.

* Replace `/path/to/your/notes` with the absolute path to your Markdown notes folder.

---

## Python Virtual Environment

### Prerequisites

* Python 3.10+
* [FastMCP](https://github.com/jlowin/fastmcp)

### Installation

```bash
git clone https://github.com/macanolli/KnowledgeBaseMCP.git
cd KnowledgeBaseMCP

python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
```

### Configuration

Create a `.env` file (or copy from `.env.example`):

```bash
KB_DIR=/path/to/your/notes
KB_DB=/path/to/database/kb_index.db

# Optional: Enable automatic Git sync
GIT_TOKEN=your_github_personal_access_token

# Optional: Transport mode
MCP_TRANSPORT=stdio  # or 'sse'
PORT=3399
HOST=0.0.0.0
```

### Run the Server

```bash
python server.py
```

---

## Available MCP Tools

| Tool                | Description                      |
| ------------------- | -------------------------------- |
| `search_notes`      | Full-text search across notes    |
| `read_note`         | Read the full contents of a note |
| `list_recent_notes` | List recently modified notes     |
| `create_note`       | Create a new note with metadata  |
| `update_note`       | Replace existing note content    |
| `append_to_note`    | Append content to a note         |
| `reindex_kb`        | Rebuild the search index         |
| `get_kb_stats`      | View knowledge base statistics   |

---

## Usage Examples

```
"Search my notes for Python async"
"Create a note about Docker networking"
"Show my recent notes"
"Add these instructions to my knowledge base"
```

---

## Project Structure

```
KnowledgeBaseMCP/
├── server.py          # MCP server entry point
├── database.py        # SQLite and indexing logic
├── tools.py           # MCP tool implementations
├── .env               # Environment configuration
└── requirements.txt   # Python dependencies
```

---

## How It Works

1. **Indexes** Markdown files from `KB_DIR` into a SQLite database
2. **Parses** YAML frontmatter for structured metadata
3. **Uses FTS5** for fast and accurate full-text search
4. **Auto-reindexes** when notes are created or modified via MCP tools
5. **Optionally syncs with Git**, committing and pushing changes automatically

---

## Advanced Configuration

### Automatic Git Sync

If your notes directory is a Git repository, the server can automatically commit and push changes when notes are created, updated, or appended.

#### Setup

1. Initialize Git in your notes directory:

   ```bash
   cd /path/to/your/notes
   git init
   git remote add origin https://github.com/yourusername/your-notes-repo.git
   ```

2. Create a GitHub Personal Access Token:

   * Visit: [https://github.com/settings/tokens](https://github.com/settings/tokens)
   * Generate a **classic** token
   * Enable the **repo** scope
   * Copy the token

3. Add the token to your `.env` file:

   ```bash
   GIT_TOKEN=ghp_your_token_here
   ```

4. Restart the server

#### What Happens Automatically

* **Create note** → `Created note: title`
* **Update note** → `Updated note: filename`
* **Append note** → `Appended to note: filename`

Each operation pulls with rebase before pushing to the remote repository.

---

### Transport Modes

#### STDIO Mode (Default)

* Local communication over standard input/output
* Designed for Claude Desktop and local MCP clients
* Configure with:

  ```bash
  MCP_TRANSPORT=stdio
  ```

#### SSE Mode (HTTP Server)

* Server-Sent Events over HTTP
* Enables remote access to your knowledge base
* Configure with:

  ```bash
  MCP_TRANSPORT=sse
  PORT=3399
  HOST=0.0.0.0
  ```
* Access the server at: `http://your-server:3399`

---

## License

MIT

---

## Contributing

Pull requests are welcome! Please follow the existing structure:

* **`database.py`** — database and indexing logic
* **`tools.py`** — MCP tool implementations
* **`server.py`** — MCP decorators and server setup

