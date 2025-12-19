
# Knowledge Base MCP Server

The **Knowledge Base MCP Server** is a Model Context Protocol (MCP) server designed for managing, indexing, and searching personal Markdown notes. It provides fast full-text search, structured metadata support, and optional Git-based synchronization, making it ideal for personal knowledge bases and MCP-enabled clients.

---

## Table of Contents

- [Features](#features)
- [Quick Start](#quick-start)
- [Setup Guide](#setup-guide)
  - [Step 1: Prepare Your Notes Directory](#step-1-prepare-your-notes-directory)
  - [Step 2: Docker Deployment (Recommended)](#step-2-docker-deployment-recommended)
  - [Alternative: Python Virtual Environment](#alternative-python-virtual-environment)
- [Available MCP Tools](#available-mcp-tools)
- [Small LLM Support](#small-llm-support)
- [Advanced Configuration](#advanced-configuration)
- [Project Structure](#project-structure)
- [Contributing](#contributing)

---

## Features

* 📝 **Create, update, and append** Markdown notes
* 🔍 **Full-text search** with snippet highlighting (SQLite FTS5)
* 🏷️ **YAML frontmatter** support for tags and metadata
* 📊 **Knowledge base statistics** and recently modified notes
* 🔄 **Automatic indexing** on startup and after updates
* 🔀 **Git synchronization (optional)** — auto-commit and push changes
* 🌐 **Multiple transport modes** — STDIO (local) or SSE (HTTP server)
* 🤖 **Small LLM optimization** — Token-efficient tools and smart routing for models like Llama 3.1 8B

---

## Quick Start

```bash
# Clone the repository
git clone https://github.com/macanolli/KnowledgeBaseMCP.git
cd KnowledgeBaseMCP

# Configure environment
cp .env.example .env
# Edit .env with your notes directory path

# Run with Docker
docker-compose up -d
```

---

## Setup Guide

### Step 1: Prepare Your Notes Directory

Before deploying the server, set up your notes directory with optional Git version control.

#### Option A: Use Existing Notes Directory

If you already have a folder of Markdown notes:

```bash
# Just note the path - you'll configure it in Step 2
/path/to/your/existing/notes
```

#### Option B: Create New Notes Directory with Git

For automatic Git synchronization, initialize version control first:

```bash
# Create and initialize directory
mkdir -p ~/my-knowledge-base
cd ~/my-knowledge-base
git init

# Add remote repository
git remote add origin https://github.com/yourusername/your-notes-repo.git

# Create initial commit
echo "# My Knowledge Base" > README.md
git add README.md
git commit -m "Initial commit"
git push -u origin main
```

**Get a GitHub Personal Access Token** (for automatic sync):

1. Visit [https://github.com/settings/tokens](https://github.com/settings/tokens)
2. Generate a **classic** token
3. Enable the **repo** scope
4. Copy the token (you'll need it in Step 2)

---

### Step 2: Docker Deployment (Recommended)

Now that your notes directory is ready, configure and deploy the MCP server.

#### 2.1 Clone This Repository

```bash
git clone https://github.com/macanolli/KnowledgeBaseMCP.git
cd KnowledgeBaseMCP
```

#### 2.2 Configure Environment

Create a `.env` file:

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```bash
# REQUIRED: Path to your notes directory from Step 1
KB_DIR=/path/to/your/notes  # Use absolute path

# Database location (inside container)
KB_DB=/data/db/kb_index.db

# OPTIONAL: Enable automatic Git sync (requires token from Step 1)
GIT_TOKEN=ghp_your_github_token_here

# OPTIONAL: Transport mode
MCP_TRANSPORT=stdio  # or 'sse' for HTTP server
PORT=3399
HOST=0.0.0.0
```

#### 2.3 Configure Git Identity (if Git sync enabled)

```bash
cp .gitconfig-docker.example .gitconfig-docker
```

Edit `.gitconfig-docker`:

```ini
[user]
  name = Your Name
  email = your.email@example.com
```

This file is mounted into the container and used when committing changes.

#### 2.4 Start the Server

```bash
docker-compose up -d
```

#### Docker Volume Notes

* **Notes directory** (`KB_DIR` → `/data/notes` in container)
  - Mounted with read-write access by default
  - Add `:ro` to the volume mount in `docker-compose.yml` for read-only access

* **Database directory** (`/data/db`)
  - Persists the search index across container restarts
  - Automatically created on first run

---

### Alternative: Python Virtual Environment

If you prefer to run the server without Docker:

#### Prerequisites

* Python 3.10+
* [FastMCP](https://github.com/jlowin/fastmcp) 2.0+

#### Installation

```bash
# Clone repository
git clone https://github.com/macanolli/KnowledgeBaseMCP.git
cd KnowledgeBaseMCP

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

#### Configuration

Create a `.env` file:

```bash
cp .env.example .env
```

Edit `.env`:

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

#### Run the Server

```bash
python server.py
```

---

## Available MCP Tools

### Core Tools

| Tool                | Description                                  |
| ------------------- | -------------------------------------------- |
| `search_notes`      | Full-text search across notes with snippets  |
| `read_note`         | Read the full contents of a note             |
| `list_recent_notes` | List recently modified notes                 |
| `create_note`       | Create a new note with metadata              |
| `update_note`       | Replace existing note content                |
| `append_to_note`    | Append content to a note                     |
| `create_directory`  | Create directories within knowledge base     |
| `reindex_kb`        | Rebuild the search index                     |
| `get_kb_stats`      | View knowledge base statistics               |

### Small LLM Optimization Tools

These tools are designed for token efficiency and easier tool selection with smaller language models (e.g., Llama 3.1 8B):

| Tool                 | Description                                       |
| -------------------- | ------------------------------------------------- |
| `what_should_i_do`   | Smart router that suggests the right tool to use |
| `quick_search`       | Lightweight search (titles/paths only, no snippets) |
| `get_note_summary`   | Get brief summary before reading full note       |

**See [SMALL_LLM_GUIDE.md](SMALL_LLM_GUIDE.md) for detailed optimization strategies.**

---

## Small LLM Support

This server includes specialized features for lower-powered language models (under 10B parameters):

### Key Benefits

* **85% tool selection accuracy** vs 40% without helper tools
* **60-85% token reduction** through optimized workflows
* **Smart routing** via natural language intent matching

### Quick Example

```python
# Small model unsure which tool to use:
what_should_i_do("I want to jot down some meeting notes")
→ Returns: "Use tool: create_note" with instructions

# Token-efficient search:
quick_search("python async")  # Returns only titles/paths (saves ~60% tokens)

# Summary before full read:
get_note_summary("/path/to/note.md")  # ~100 token summary
→ If relevant: read_note("/path/to/note.md")  # Full content
```

### Supported Patterns

The `what_should_i_do` tool handles tricky questions like:
- "I want to jot down some quick thoughts" → `create_note`
- "What have I been working on lately?" → `list_recent_notes`
- "Where did I write about databases?" → `search_notes`
- "Add more info to my meeting notes" → `append_to_note`
- "I edited files externally" → `reindex_kb`

**Full documentation:** [SMALL_LLM_GUIDE.md](SMALL_LLM_GUIDE.md)

---

## Usage Examples

### With High-Powered Models (GPT-4, Claude, etc.)

```
"Search my notes for Python async"
"Create a note about Docker networking"
"Show my recent notes"
"Add these instructions to my knowledge base"
```

### With Small Models (Llama 3.1 8B, etc.)

```
"what should i do: I want to save some meeting notes"
"quick search: python async"
"get note summary: /path/to/note.md"
```

---

## Project Structure

```
KnowledgeBaseMCP/
├── server.py              # MCP server entry point (FastMCP decorators)
├── database.py            # SQLite operations, indexing, Git integration
├── tools.py               # MCP tool implementations
├── .env                   # Environment configuration
├── .gitconfig-docker      # Git identity for Docker commits
├── requirements.txt       # Python dependencies
├── docker-compose.yml     # Docker deployment configuration
├── Dockerfile             # Container image definition
├── SMALL_LLM_GUIDE.md     # Optimization guide for small models
└── data/
    ├── notes/             # Your Markdown notes (mounted volume)
    └── db/
        └── kb_index.db    # SQLite database with FTS5 index
```

### Database Schema

The SQLite database includes:

* **`notes`** — Main table with file metadata
* **`notes_fts`** — FTS5 virtual table for full-text search
* **`tool_prompts`** — Instructions and keywords for small LLM routing
* **`note_summaries`** — Cached summaries for token efficiency
* **`query_cache`** — Query result caching (future use)

---

## Advanced Configuration

### Git Synchronization Details

If you set up Git in [Step 1](#step-1-prepare-your-notes-directory), the server automatically:

#### Automatic Operations

* **On startup** → Pulls latest changes from remote
* **Create note** → Commits with message: `Created note: title`
* **Update note** → Commits with message: `Updated note: filename`
* **Append note** → Commits with message: `Appended to note: filename`

Each operation pulls with rebase before pushing to avoid conflicts.

#### Offline Behavior

* Changes are committed locally when network is unavailable
* Syncs automatically when connection is restored
* Your local files are always safe

#### Security

* GitHub token is passed via environment variable (never stored in `.git/config`)
* Uses temporary credential helpers for authentication
* Supports HTTPS GitHub URLs only

---

## How It Works

1. **Indexes** Markdown files from `KB_DIR` into a SQLite database
2. **Parses** YAML frontmatter for structured metadata
3. **Uses FTS5** for fast and accurate full-text search
4. **Auto-reindexes** when notes are created or modified via MCP tools
5. **Optionally syncs with Git**, committing and pushing changes automatically
6. **Caches summaries** in `note_summaries` table for token efficiency

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

## Contributing

Pull requests are welcome! Please follow the existing structure:

* **`database.py`** — Database operations, indexing, Git integration
* **`tools.py`** — MCP tool implementations (business logic)
* **`server.py`** — MCP decorators and server setup (routing only)

### Development Workflow

```bash
# Create feature branch
git checkout -b feat/your-feature

# Make changes and test
python server.py

# Verify syntax
python -m py_compile server.py database.py tools.py

# Submit PR
```

---

## License

MIT

---

## Links

* **Documentation**: [SMALL_LLM_GUIDE.md](SMALL_LLM_GUIDE.md) — Optimization strategies for small models
* **MCP Protocol**: [https://modelcontextprotocol.io](https://modelcontextprotocol.io)
* **FastMCP Framework**: [https://github.com/jlowin/fastmcp](https://github.com/jlowin/fastmcp)
* **Issues**: [https://github.com/macanolli/KnowledgeBaseMCP/issues](https://github.com/macanolli/KnowledgeBaseMCP/issues)
