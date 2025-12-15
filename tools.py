"""
MCP tools for the Knowledge Base server.

Defines all available tools/functions that can be called via MCP.
"""

from pathlib import Path
from fastmcp import Context

from database import (
    search_notes_db,
    get_recent_notes,
    get_kb_statistics,
    index_directory,
    create_note_file,
    update_note_file,
    append_to_note_file,
    index_file,
    upsert_note_to_db,
    git_commit_and_push
)


async def search_notes(query: str, db_path: str, limit: int = 10) -> str:
    """
    Search through your knowledge base notes.

    Args:
        query: Search terms (searches title, content, tags, and filename)
        limit: Maximum number of results to return (default: 10)
        :param limit:
        :param query:
        :param db_path:
    """
    results = search_notes_db(query, db_path, limit)

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


async def reindex_kb(ctx: Context, kb_dir: str, db_path: str) -> str:
    """Reindex all Markdown files in the knowledge base directory."""
    await ctx.info(f"Starting reindex of {kb_dir}...")
    count = index_directory(kb_dir, db_path)
    message = f"Successfully indexed {count} notes from {kb_dir}"
    await ctx.info(message)
    return message


async def list_recent_notes(db_path: str, limit: int = 20) -> str:
    """List the most recently modified notes."""
    results = get_recent_notes(db_path, limit)

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


async def get_kb_stats(kb_dir: str, db_path: str) -> str:
    """Get statistics about your knowledge base."""
    stats = get_kb_statistics(db_path)

    return f"""Knowledge Base Statistics:
- Total notes: {stats['total_notes']}
- Total content: {stats['total_chars']:,} characters
- Directory: {kb_dir}
- Last indexed: {stats['last_indexed'] or 'Never'}"""


async def create_note(title: str, content: str, kb_dir: str, db_path: str, tags: str = "", ctx: Context = None) -> str:
    """Create a new note in the knowledge base.
    
    Args:
        title: Title of the note (will be used as filename and H1 heading)
        content: Content of the note (markdown supported)
        kb_dir: Knowledge base directory
        db_path: Database path
        tags: Optional comma-separated tags
        ctx: MCP context for logging
    
    Returns:
        Confirmation message with filepath
    """
    filepath, error = create_note_file(kb_dir, title, content, tags)
    
    if error:
        return f"Error: {error}"
    
    # Index the new note
    try:
        note_data = index_file(filepath)
        upsert_note_to_db(note_data, db_path)

        if ctx:
            await ctx.info(f"Created note: {filepath}")

        # Git commit and push
        success, git_message = git_commit_and_push(kb_dir, f"Created note: {title}")
        if success:
            if ctx:
                await ctx.info(f"Git: {git_message}")
            git_status = f"\n\n📦 Git: {git_message}"
        else:
            if ctx:
                await ctx.warning(f"Git: {git_message}")
            git_status = f"\n\n⚠️ Git: {git_message}"

        return f"Successfully created note '{title}' at:\n{filepath}{git_status}"
    except Exception as e:
        return f"Error indexing new note: {e}"


async def update_note(filepath: str, content: str, db_path: str, ctx: Context = None) -> str:
    """Update an existing note's content (replaces entire content).
    
    Args:
        filepath: Full path to the note file
        content: New content for the note (will completely replace existing content)
        db_path: Database path
        ctx: MCP context for logging
    
    Returns:
        Confirmation message
    """
    note_path = Path(filepath)
    
    error = update_note_file(note_path, content)
    if error:
        return f"Error: {error}"
    
    # Re-index the note
    try:
        note_data = index_file(note_path)
        upsert_note_to_db(note_data, db_path)

        if ctx:
            await ctx.info(f"Updated note: {filepath}")

        # Find git root by walking up from note_path.parent
        git_root = None
        current = note_path.parent
        while current != current.parent:
            if (current / ".git").exists():
                git_root = current
                break
            current = current.parent

        # Git commit and push
        if git_root:
            success, git_message = git_commit_and_push(str(git_root), f"Updated note: {note_path.name}")
            if success:
                if ctx:
                    await ctx.info(f"Git: {git_message}")
                git_status = f"\n\n📦 Git: {git_message}"
            else:
                if ctx:
                    await ctx.warning(f"Git: {git_message}")
                git_status = f"\n\n⚠️ Git: {git_message}"
        else:
            git_status = "\n\n⚠️ Git: Not a git repository"
            if ctx:
                await ctx.warning("Git: Not a git repository")

        return f"Successfully updated note at:\n{filepath}{git_status}"
    except Exception as e:
        return f"Error re-indexing updated note: {e}"


async def append_to_note(filepath: str, content: str, db_path: str, ctx: Context = None) -> str:
    """Append content to an existing note (adds to the end).
    
    Args:
        filepath: Full path to the note file
        content: Content to append to the note
        db_path: Database path
        ctx: MCP context for logging
    
    Returns:
        Confirmation message
    """
    note_path = Path(filepath)
    
    error = append_to_note_file(note_path, content)
    if error:
        return f"Error: {error}"
    
    # Re-index the note
    try:
        note_data = index_file(note_path)
        upsert_note_to_db(note_data, db_path)

        if ctx:
            await ctx.info(f"Appended to note: {filepath}")

        # Find git root by walking up from note_path.parent
        git_root = None
        current = note_path.parent
        while current != current.parent:
            if (current / ".git").exists():
                git_root = current
                break
            current = current.parent

        # Git commit and push
        if git_root:
            success, git_message = git_commit_and_push(str(git_root), f"Appended to note: {note_path.name}")
            if success:
                if ctx:
                    await ctx.info(f"Git: {git_message}")
                git_status = f"\n\n📦 Git: {git_message}"
            else:
                if ctx:
                    await ctx.warning(f"Git: {git_message}")
                git_status = f"\n\n⚠️ Git: {git_message}"
        else:
            git_status = "\n\n⚠️ Git: Not a git repository"
            if ctx:
                await ctx.warning("Git: Not a git repository")

        return f"Successfully appended to note at:\n{filepath}{git_status}"
    except Exception as e:
        return f"Error re-indexing appended note: {e}"
