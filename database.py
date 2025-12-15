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


def upsert_note_to_db(note_data: Dict[str, Any], db_path: str):
    """Insert or update a note in the database and FTS index."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

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

    conn.commit()
    conn.close()


def create_note_file(kb_dir: str, title: str, content: str, tags: str = "") -> tuple[Path, str]:
    """Create a new markdown file with proper formatting.
    
    Returns:
        tuple: (filepath, error_message) - error_message is empty string on success
    """
    # Sanitize filename
    filename = re.sub(r'[^\w\s-]', '', title.lower())
    filename = re.sub(r'[-\s]+', '-', filename)
    filename = f"{filename}.md"

    filepath = Path(kb_dir) / filename

    # Check if file already exists
    if filepath.exists():
        return filepath, f"Note '{filename}' already exists. Use update_note to modify it."

    # Create frontmatter if tags provided
    frontmatter = ""
    if tags:
        frontmatter = f"---\ntitle: {title}\ntags: {tags}\n---\n\n"

    # Build full content
    full_content = f"{frontmatter}# {title}\n\n{content}"

    # Write file
    try:
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(full_content)
        return filepath, ""
    except Exception as e:
        return filepath, f"Error creating file: {e}"


def update_note_file(filepath: Path, content: str) -> str:
    """Update an existing note file, preserving frontmatter.
    
    Returns:
        Empty string on success, error message on failure
    """
    if not filepath.exists():
        return f"Note not found at {filepath}"

    try:
        # Read existing frontmatter if present
        with open(filepath, 'r', encoding='utf-8') as f:
            old_content = f.read()

        frontmatter, _ = extract_frontmatter(old_content)

        # Preserve frontmatter if it exists
        if frontmatter:
            fm_lines = ["---"]
            for key, value in frontmatter.items():
                fm_lines.append(f"{key}: {value}")
            fm_lines.append("---\n")
            full_content = "\n".join(fm_lines) + "\n" + content
        else:
            full_content = content

        # Write updated content
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(full_content)

        return ""
    except Exception as e:
        return f"Error updating note: {e}"


def append_to_note_file(filepath: Path, content: str) -> str:
    """Append content to an existing note file.
    
    Returns:
        Empty string on success, error message on failure
    """
    if not filepath.exists():
        return f"Note not found at {filepath}"

    try:
        # Read existing content
        with open(filepath, 'r', encoding='utf-8') as f:
            existing_content = f.read()

        # Append new content
        updated_content = existing_content.rstrip() + "\n\n" + content

        # Write back
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(updated_content)

        return ""
    except Exception as e:
        return f"Error appending to note: {e}"


def git_commit_and_push(kb_dir: str, message: str) -> tuple[bool, str]:
    """
    Commit and push changes to git repo.

    Returns:
        tuple: (success: bool, message: str)
    """
    import subprocess

    repo_path = Path(kb_dir)

    try:
        # Check if it's a git repo
        result = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode != 0:
            return False, "Not a git repository"

        # Get current branch name
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode != 0:
            return False, "Failed to get current branch"

        current_branch = result.stdout.strip()
        if not current_branch:
            return False, "Not on a branch (detached HEAD)"

        # Configure git credential helper if GIT_TOKEN is available
        git_token = os.environ.get("GIT_TOKEN")
        if git_token:
            # Get the remote URL
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=5
            )
            remote_url = result.stdout.strip()

            # If using HTTPS, inject token into URL
            if remote_url.startswith("https://github.com/"):
                auth_url = remote_url.replace("https://", f"https://{git_token}@")
                subprocess.run(
                    ["git", "remote", "set-url", "origin", auth_url],
                    cwd=repo_path,
                    capture_output=True,
                    timeout=5
                )

        # Stage all changes
        subprocess.run(
            ["git", "add", "."],
            cwd=repo_path,
            check=True,
            capture_output=True,
            timeout=10
        )

        # Check if there are changes to commit
        result = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=repo_path,
            capture_output=True
        )

        if result.returncode == 0:
            return True, "No changes to commit"

        # Commit
        subprocess.run(
            ["git", "commit", "-m", message],
            cwd=repo_path,
            check=True,
            capture_output=True,
            timeout=10
        )

        # Pull with rebase (using current branch)
        subprocess.run(
            ["git", "pull", "--rebase", "origin", current_branch],
            cwd=repo_path,
            check=True,
            capture_output=True,
            timeout=30
        )

        # Push (using current branch)
        subprocess.run(
            ["git", "push", "origin", current_branch],
            cwd=repo_path,
            check=True,
            capture_output=True,
            timeout=30
        )

        return True, f"Successfully committed and pushed changes to {current_branch}"

    except subprocess.TimeoutExpired:
        return False, "Git operation timed out"
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode() if e.stderr else str(e)
        return False, f"Git error: {error_msg}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"