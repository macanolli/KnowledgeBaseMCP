"""
Database operations for the Knowledge Base MCP Server.

Handles SQLite database initialization, indexing, and queries.
"""

import sqlite3
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
import re


def init_db(db_path: str):
    """Initialize the SQLite database for storing indexed notes."""
    conn = sqlite3.connect(db_path)
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


def index_directory(directory: str, db_path: str) -> int:
    """Index all Markdown files in the directory."""
    conn = sqlite3.connect(db_path)
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


def search_notes_db(query: str, db_path: str, limit: int = 10) -> list:
    """Search through indexed notes."""
    conn = sqlite3.connect(db_path)
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

    return results


def get_recent_notes(db_path: str, limit: int = 20) -> list:
    """Get the most recently modified notes."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
                   SELECT title, filepath, filename, modified_at, tags
                   FROM notes
                   ORDER BY modified_at DESC LIMIT ?
                   """, (limit,))

    results = cursor.fetchall()
    conn.close()

    return results


def get_kb_statistics(db_path: str) -> dict:
    """Get statistics about the knowledge base."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM notes")
    total_notes = cursor.fetchone()[0]

    cursor.execute("SELECT MAX(indexed_at) FROM notes")
    last_indexed = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(LENGTH(content)) FROM notes")
    total_chars = cursor.fetchone()[0] or 0

    conn.close()

    return {
        'total_notes': total_notes,
        'last_indexed': last_indexed,
        'total_chars': total_chars
    }
