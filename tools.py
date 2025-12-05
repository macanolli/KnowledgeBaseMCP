"""
MCP tools for the Knowledge Base server.

Defines all available tools/functions that can be called via MCP.
"""

from pathlib import Path
from fastmcp import Context

from database import search_notes_db, get_recent_notes, get_kb_statistics, index_directory


async def search_notes(query: str, db_path: str, limit: int = 10) -> str:
    """
    Search through your knowledge base notes.

    Args:
        query: Search terms (searches title, content, tags, and filename)
        limit: Maximum number of results to return (default: 10)
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
