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

# Configuration - customize these paths in .env file
KB_DIR = os.getenv("KB_DIR", str(Path.home() / "knowledge_base"))
DB_PATH = os.getenv("KB_DB", str(Path.home() / ".kb_index.db"))


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