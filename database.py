"""
Database operations for the Knowledge Base MCP Server.

Handles SQLite database initialization, indexing, and queries.
"""

import sqlite3
import sys
import os
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


def index_directory(directory: str, db_path: str) -> tuple[int, int]:
    """Index all Markdown files in the directory and remove orphaned entries.

    Returns:
        tuple: (indexed_count, removed_count)
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    kb_path = Path(directory)

    if not kb_path.exists():
        kb_path.mkdir(parents=True, exist_ok=True)
        return 0, 0

    # Step 1: Get all files currently on filesystem
    filesystem_files = set()
    for md_file in kb_path.rglob("*.md"):
        filesystem_files.add(str(md_file))

    # Step 2: Get all files currently in database
    cursor.execute("SELECT filepath FROM notes")
    db_files = {row[0] for row in cursor.fetchall()}

    # Step 3: Find orphaned entries (in DB but not on filesystem)
    orphaned_files = db_files - filesystem_files

    # Step 4: Remove orphaned entries from both tables
    removed_count = 0
    for filepath in orphaned_files:
        # Delete from FTS table first (foreign key constraint)
        cursor.execute("DELETE FROM notes_fts WHERE rowid IN (SELECT id FROM notes WHERE filepath = ?)", (filepath,))
        # Delete from notes table
        cursor.execute("DELETE FROM notes WHERE filepath = ?", (filepath,))
        removed_count += 1
        print(f"Removed orphaned entry: {filepath}", file=sys.stderr)

    # Step 5: Index/update all current files
    indexed_count = 0
    for md_file_path in filesystem_files:
        try:
            md_file = Path(md_file_path)
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

            indexed_count += 1
        except Exception as e:
            print(f"Error indexing {md_file}: {e}", file=sys.stderr)

    conn.commit()
    conn.close()

    return indexed_count, removed_count


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
    Commit and push changes to git repo using GitPython with secure credential handling.

    Returns:
        tuple: (success: bool, message: str)
    """
    from git import Repo, InvalidGitRepositoryError, GitCommandError

    repo_path = Path(kb_dir)

    try:
        # Check if it's a git repo and open it
        try:
            repo = Repo(repo_path)
        except InvalidGitRepositoryError:
            return False, "Not a git repository"

        # Check if we're in a detached HEAD state
        if repo.head.is_detached:
            return False, "Not on a branch (detached HEAD)"

        # Get current branch name
        current_branch = repo.active_branch.name

        # Stage all changes
        repo.git.add(A=True)

        # Check if there are changes to commit
        if not repo.index.diff("HEAD") and not repo.untracked_files:
            return True, "No changes to commit"

        # Commit
        repo.index.commit(message)

        # Prepare secure environment for git operations if GIT_TOKEN is available
        git_token = os.environ.get("GIT_TOKEN")
        custom_env = None

        if git_token and 'origin' in repo.remotes:
            remote_url = repo.remotes.origin.url

            # Only use token for HTTPS GitHub URLs
            if remote_url.startswith("https://github.com/"):
                # Create custom environment with GIT_ASKPASS
                # This passes credentials without modifying .git/config
                import tempfile
                import stat

                # Create a temporary script that returns the token
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.sh') as f:
                    f.write('#!/bin/sh\n')
                    f.write(f'echo "{git_token}"\n')
                    askpass_script = f.name

                # Make script executable
                os.chmod(askpass_script, stat.S_IRUSR | stat.S_IXUSR)

                # Set up custom environment
                custom_env = os.environ.copy()
                custom_env['GIT_ASKPASS'] = askpass_script
                custom_env['GIT_USERNAME'] = git_token  # For GitHub, username can be the token
                custom_env['GIT_PASSWORD'] = git_token

        try:
            # Pull with rebase (using current branch)
            origin = repo.remotes.origin
            if custom_env:
                origin.pull(current_branch, rebase=True, env=custom_env)
            else:
                origin.pull(current_branch, rebase=True)

            # Push (using current branch)
            if custom_env:
                origin.push(current_branch, env=custom_env)
            else:
                origin.push(current_branch)
        finally:
            # Clean up temporary askpass script
            if custom_env and 'GIT_ASKPASS' in custom_env:
                try:
                    os.unlink(custom_env['GIT_ASKPASS'])
                except Exception:
                    pass

        return True, f"Successfully committed and pushed changes to {current_branch}"

    except GitCommandError as e:
        return False, f"Git error: {str(e)}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"


def git_pull_from_remote(kb_dir: str) -> tuple[bool, str]:
    """
    Pull changes from the remote git repository using GitPython with secure credential handling.
    Used to sync notes from other machines before listing or reindexing.

    Returns:
        tuple: (success: bool, message: str)
    """
    from git import Repo, InvalidGitRepositoryError, GitCommandError

    repo_path = Path(kb_dir)

    try:
        # Check if it's a git repo and open it
        try:
            repo = Repo(repo_path)
        except InvalidGitRepositoryError:
            return False, "Not a git repository"

        # Check if we're in a detached HEAD state
        if repo.head.is_detached:
            return False, "Not on a branch (detached HEAD)"

        # Get current branch name
        current_branch = repo.active_branch.name

        # Prepare secure environment for git operations if GIT_TOKEN is available
        git_token = os.environ.get("GIT_TOKEN")
        custom_env = None

        if git_token and 'origin' in repo.remotes:
            remote_url = repo.remotes.origin.url

            # Only use token for HTTPS GitHub URLs
            if remote_url.startswith("https://github.com/"):
                # Create custom environment with GIT_ASKPASS
                # This passes credentials without modifying .git/config
                import tempfile
                import stat

                # Create a temporary script that returns the token
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.sh') as f:
                    f.write('#!/bin/sh\n')
                    f.write(f'echo "{git_token}"\n')
                    askpass_script = f.name

                # Make script executable
                os.chmod(askpass_script, stat.S_IRUSR | stat.S_IXUSR)

                # Set up custom environment
                custom_env = os.environ.copy()
                custom_env['GIT_ASKPASS'] = askpass_script
                custom_env['GIT_USERNAME'] = git_token  # For GitHub, username can be the token
                custom_env['GIT_PASSWORD'] = git_token

        try:
            # Fetch from remote
            origin = repo.remotes.origin
            if custom_env:
                origin.fetch(current_branch, env=custom_env)
            else:
                origin.fetch(current_branch)

            # Check if we're behind remote
            try:
                # Count commits between HEAD and origin/current_branch
                commits_behind = sum(1 for _ in repo.iter_commits(f'HEAD..origin/{current_branch}'))
            except Exception:
                commits_behind = 0

            if commits_behind == 0:
                return True, "Already up to date"

            # Pull with rebase to avoid merge commits
            try:
                if custom_env:
                    origin.pull(current_branch, rebase=True, env=custom_env)
                else:
                    origin.pull(current_branch, rebase=True)
            except GitCommandError as e:
                # If rebase fails, try to abort
                try:
                    repo.git.rebase(abort=True)
                except Exception:
                    pass
                return False, f"Git pull failed: {str(e)}"

            return True, f"Pulled {commits_behind} commit(s) from {current_branch}"

        finally:
            # Clean up temporary askpass script
            if custom_env and 'GIT_ASKPASS' in custom_env:
                try:
                    os.unlink(custom_env['GIT_ASKPASS'])
                except Exception:
                    pass

    except GitCommandError as e:
        return False, f"Git error: {str(e)}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"