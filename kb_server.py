"""
Personal Knowledge Base MCP Server

Indexes markdown files from a directory and provides search capabilities.
"""

import os
import sys
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
import re

from fastmcp import FastMCP, Context

# Initialize the MCP server
mcp = FastMCP("Knowledge Base")

# Configuration - customize these paths
KB_DIR = os.getenv("KB_DIR", str(Path.home() / "knowledge_base"))
DB_PATH = os.getenv("KB_DB", str(Path.home() / ".kb_index.db"))


def init_db():
    """Initialize the SQLite database for storing indexed notes."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS notes
                   (
                       id INTEGER PRIMARY KEY AUTOINCREMENT,
                       filepath TEXT UNIQUE NOT NULL,
                       filename TEXT NOT NULL, 
                       title TEXT,
                       content TEXT NOT NULL,
                       tags TEXT,
                       created_at TEXT,
                       modified_at TEXT,
                       indexed_at TEXT NOT NULL
                   )
                   """)

    # Create a full-text search virtual table
    cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(
            filepath,
            filename, 
            title,
            content,
            tags,
            content='notes',
            content_rowid='id'
        )
    """)

    conn.commit()
    conn.close()


def extract_frontmatter(content: str) -> tuple:
    """Extract YAML frontmatter from the Markdown content."""
    frontmatter = {}

    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            fm_text = parts[1]
            content = parts[2].strip()

            for line in fm_text.strip().split("\n"):
                if ":" in line:
                    key, value = line.split(":", 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    frontmatter[key] = value

    return frontmatter, content


def index_file(filepath: Path) -> Dict[str, Any]:
    """Index a single Markdown file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    frontmatter, body = extract_frontmatter(content)

    # Extract title
    title = frontmatter.get('title', '')
    if not title:
        match = re.search(r'^#\s+(.+)$', body, re.MULTILINE)
        if match:
            title = match.group(1)
        else:
            title = filepath.stem

    # Get tags
    tags = frontmatter.get('tags', '')
    if isinstance(tags, list):
        tags = ', '.join(tags)

    # Get file timestamps
    stat = filepath.stat()
    created_at = datetime.fromtimestamp(stat.st_ctime).isoformat()
    modified_at = datetime.fromtimestamp(stat.st_mtime).isoformat()

    return {
        'filepath': str(filepath),
        'filename': filepath.name,
        'title': title,
        'content': body,
        'tags': tags,
        'created_at': created_at,
        'modified_at': modified_at,
        'indexed_at': datetime.now().isoformat()
    }


def index_directory(directory: str) -> int:
    """Index all Markdown files in the directory."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    idx = 0
    kb_path = Path(directory)

    if not kb_path.exists():
        kb_path.mkdir(parents=True, exist_ok=True)
        return 0

    for md_file in kb_path.rglob("*.md"):
        try:
            note_data = index_file(md_file)

            cursor.execute("""
                INSERT OR REPLACE INTO notes 
                (filepath, filename, title, content, tags, created_at, modified_at, indexed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                note_data['filepath'],
                note_data['filename'],
                note_data['title'],
                note_data['content'],
                note_data['tags'],
                note_data['created_at'],
                note_data['modified_at'],
                note_data['indexed_at']
            ))

            cursor.execute("""
                INSERT OR REPLACE INTO notes_fts 
                (rowid, filepath, filename, title, content, tags)
                SELECT id, filepath, filename, title, content, tags 
                FROM notes WHERE filepath = ?
            """, (note_data['filepath'],))

            idx += 1
        except Exception as e:
            print(f"Error indexing {md_file}: {e}", file=sys.stderr)

    conn.commit()
    conn.close()

    return idx


@mcp.tool
async def search_notes(query: str, limit: int = 10) -> str:
    """
    Search through your knowledge base notes.

    Args:
        query: Search terms (searches title, content, tags, and filename)
        limit: Maximum number of results to return (default: 10)
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
                   SELECT n.title,
                          n.filepath,
                          n.filename,
                          n.tags,
                          snippet(notes_fts, 3, '<mark>', '</mark>', '...', 30) as snippet
                   FROM notes_fts
                            JOIN notes n ON notes_fts.rowid = n.id
                   WHERE notes_fts MATCH ?
                   ORDER BY rank LIMIT ?
                   """, (query, limit))

    results = cursor.fetchall()
    conn.close()

    if not results:
        return f"No results found for '{query}'"

    output = [f"Found {len(results)} results for '{query}':\n"]

    for i, (title, filepath, filename, tags, snippet) in enumerate(results, 1):
        output.append(f"{i}. **{title}**")
        output.append(f"   File: {filepath}")
        if tags:
            output.append(f"   Tags: {tags}")
        output.append(f"   ...{snippet}...")
        output.append("")

    return "\n".join(output)


@mcp.tool
async def read_note(filepath: str) -> str:
    """Read the complete contents of a note."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        return f"# {Path(filepath).name}\n\n{content}"
    except FileNotFoundError:
        return f"Note not found: {filepath}"
    except Exception as e:
        return f"Error reading note: {e}"


@mcp.tool
async def reindex_kb(ctx: Context) -> str:
    """Reindex all Markdown files in the knowledge base directory."""
    await ctx.info(f"Starting reindex of {KB_DIR}...")
    count = index_directory(KB_DIR)
    message = f"Successfully indexed {count} notes from {KB_DIR}"
    await ctx.info(message)
    return message


@mcp.tool
async def list_recent_notes(limit: int = 20) -> str:
    """List the most recently modified notes."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
                   SELECT title, filepath, filename, modified_at, tags
                   FROM notes
                   ORDER BY modified_at DESC LIMIT ?
                   """, (limit,))

    results = cursor.fetchall()
    conn.close()

    if not results:
        return "No notes found. Run reindex_kb first."

    output = [f"Recent notes (last {len(results)}):\n"]

    for i, (title, filepath, filename, modified_at, tags) in enumerate(results, 1):
        output.append(f"{i}. **{title}**")
        output.append(f"   File: {filepath}")
        output.append(f"   Modified: {modified_at}")
        if tags:
            output.append(f"   Tags: {tags}")
        output.append("")

    return "\n".join(output)


@mcp.tool
async def get_kb_stats() -> str:
    """Get statistics about your knowledge base."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM notes")
    total_notes = cursor.fetchone()[0]

    cursor.execute("SELECT MAX(indexed_at) FROM notes")
    last_indexed = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(LENGTH(content)) FROM notes")
    total_chars = cursor.fetchone()[0] or 0

    conn.close()

    return f"""Knowledge Base Statistics:
- Total notes: {total_notes}
- Total content: {total_chars:,} characters
- Directory: {KB_DIR}
- Last indexed: {last_indexed or 'Never'}"""


# Initialize on startup
init_db()
if Path(KB_DIR).exists():
    count = index_directory(KB_DIR)
    print(f"Indexed {count} notes from {KB_DIR}", file=sys.stderr)

if __name__ == "__main__":
    mcp.run()