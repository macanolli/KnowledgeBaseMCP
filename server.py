"""
Personal Knowledge Base MCP Server

Indexes markdown files from a directory and provides search capabilities.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

from fastmcp import FastMCP, Context

from database import init_db, index_directory
import tools

# Load environment variables from .env file
load_dotenv()

# Initialize the MCP server
mcp = FastMCP("Knowledge Base")

KB_DIR = os.getenv("KB_DIR")
DB_PATH = os.getenv("KB_DB")

if not KB_DIR or not DB_PATH:
    raise ValueError("KB_DIR and KB_DB must be set in .env file")


@mcp.tool
async def search_notes(query: str, limit: int = 10) -> str:
    """
    Search through your knowledge base notes.

    Args:
        query: Search terms (searches title, content, tags, and filename)
        limit: Maximum number of results to return (default: 10)
    """
    return await tools.search_notes(query, DB_PATH, limit)


@mcp.tool
async def read_note(filepath: str) -> str:
    """Read the complete contents of a note."""
    return await tools.read_note(filepath)


@mcp.tool
async def reindex_kb(ctx: Context) -> str:
    """Reindex all Markdown files in the knowledge base directory."""
    return await tools.reindex_kb(ctx, KB_DIR, DB_PATH)


@mcp.tool
async def list_recent_notes(limit: int = 20) -> str:
    """List the most recently modified notes."""
    return await tools.list_recent_notes(DB_PATH, limit)


@mcp.tool
async def get_kb_stats() -> str:
    """Get statistics about your knowledge base."""
    return await tools.get_kb_stats(KB_DIR, DB_PATH)


@mcp.tool
async def create_note(title: str, content: str, tags: str = "", ctx: Context = None) -> str:
    """
    Create a new note in the knowledge base.
    
    Args:
        title: Title of the note (will be used as filename and H1 heading)
        content: Content of the note (markdown supported)
        tags: Optional comma-separated tags
    
    Returns:
        Confirmation message with filepath
    """
    return await tools.create_note(title, content, KB_DIR, DB_PATH, tags, ctx)


@mcp.tool
async def update_note(filepath: str, content: str, ctx: Context = None) -> str:
    """
    Update an existing note's content (replaces entire content).
    
    Args:
        filepath: Full path to the note file
        content: New content for the note (will completely replace existing content)
    
    Returns:
        Confirmation message
    """
    return await tools.update_note(filepath, content, DB_PATH, ctx)


@mcp.tool
async def append_to_note(filepath: str, content: str, ctx: Context = None) -> str:
    """
    Append content to an existing note (adds to the end).
    
    Args:
        filepath: Full path to the note file
        content: Content to append to the note
    
    Returns:
        Confirmation message
    """
    return await tools.append_to_note(filepath, content, DB_PATH, ctx)


# Initialize on startup
init_db(DB_PATH)
if Path(KB_DIR).exists():
    count = index_directory(KB_DIR, DB_PATH)
    print(f"Indexed {count} notes from {KB_DIR}", file=sys.stderr)

if __name__ == "__main__":
    try:
        mcp.run()
    except KeyboardInterrupt:
        print("\nShutting down gracefully...", file=sys.stderr)
        sys.exit(0)
