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
    git_commit_and_push,
    git_pull_from_remote,
    create_directory,
    get_tool_suggestion,
    get_note_summary,
    populate_tool_prompts
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

    # Pull from remote first to sync changes from other machines
    success, git_message = git_pull_from_remote(kb_dir)
    if success:
        await ctx.info(f"Git sync: {git_message}")
    else:
        await ctx.warning(f"Git sync: {git_message}")

    indexed_count, removed_count = index_directory(kb_dir, db_path)

    if removed_count > 0:
        message = f"Successfully indexed {indexed_count} notes and removed {removed_count} orphaned entries from {kb_dir}"
    else:
        message = f"Successfully indexed {indexed_count} notes from {kb_dir}"

    await ctx.info(message)

    # Include git sync status in the response
    if success and "Pulled" in git_message:
        return f"{message}\n\n📥 Git: {git_message}"
    elif success:
        return message
    else:
        return f"{message}\n\n⚠️ Git: {git_message}"


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


async def create_kb_directory(directory_path: str, kb_dir: str, ctx: Context = None) -> str:
    """Create a directory within the knowledge base.

    Args:
        directory_path: Relative path for the directory to create (e.g., "projects/python")
        kb_dir: Knowledge base root directory
        ctx: MCP context for logging

    Returns:
        Confirmation message
    """
    success, message = create_directory(kb_dir, directory_path)

    if ctx:
        if success:
            await ctx.info(message)
        else:
            await ctx.warning(message)

    return message


async def what_should_i_do_tool(user_request: str, db_path: str) -> str:
    """
    SMALL MODEL HELPER: Not sure which tool to use? Describe what you want to do.

    This tool helps small language models choose the right tool for the task.
    Just describe your intent in natural language.

    Examples of tricky questions this can handle:
    - "I want to jot down some quick thoughts" → create_note
    - "What have I been working on lately?" → list_recent_notes
    - "Where did I write about that database project?" → search_notes
    - "I need to add more info to my meeting notes" → append_to_note
    - "Can you tell me how many notes I have?" → get_kb_stats
    - "I edited files outside the system, need to refresh" → reindex_kb
    - "Need to organize my notes into categories" → create_directory
    - "Want to completely rewrite my old note" → update_note
    - "Let me see that Python tutorial I saved" → read_note

    Returns exact tool name and parameters to use.
    """
    suggestion = get_tool_suggestion(user_request, db_path)

    output = f"""Tool Recommendation (confidence: {suggestion['confidence']}):

**Use tool:** {suggestion['tool_name']}

**How to use it:**
{suggestion['instruction']}

**Your request:** "{user_request}"
"""

    return output


async def quick_search_tool(keywords: str, db_path: str) -> str:
    """
    SMALL MODEL: Lightweight search returning only titles and paths (no content).
    Use this to save tokens when you just need to find which notes exist.

    Args:
        keywords: Search keywords (space-separated)

    Returns:
        Compact list of top 5 matching notes with titles and filepaths only.
    """
    results = search_notes_db(keywords, db_path, limit=5)

    if not results:
        return f"No notes found matching: {keywords}"

    output = [f"Found {len(results)} notes:\n"]

    for i, (title, filepath, filename, tags, _) in enumerate(results, 1):
        output.append(f"{i}. {title}")
        output.append(f"   Path: {filepath}")
        if tags:
            output.append(f"   Tags: {tags}")

    return "\n".join(output)


async def get_summary_tool(filepath: str, db_path: str) -> str:
    """
    SMALL MODEL: Get brief summary of a note (saves tokens vs reading full content).
    Use this first to check if a note is relevant before calling read_note.

    Args:
        filepath: Full path to the note file

    Returns:
        Brief summary (max 100 tokens) with key topics
    """
    summary_data = get_note_summary(filepath, db_path)

    if summary_data['summary'] == 'Note not found':
        return f"Error: Note not found at {filepath}"

    output = f"""Summary of: {Path(filepath).name}

{summary_data['summary']}"""

    if summary_data['key_topics']:
        output += f"\n\nKey topics: {summary_data['key_topics']}"

    output += f"\n\nFull path: {filepath}"
    output += "\n\n(Use read_note to see full content)"

    return output


async def initialize_tool_prompts(db_path: str) -> str:
    """Initialize the tool_prompts table with guidance for small LLMs."""
    try:
        populate_tool_prompts(db_path)
        return "Tool prompts initialized successfully"
    except Exception as e:
        return f"Error initializing tool prompts: {e}"
