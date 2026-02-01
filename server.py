"""
Personal Knowledge Base MCP Server

Indexes markdown files from a directory and provides search capabilities.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional

from fastmcp import FastMCP, Context
from fastmcp.server.middleware import Middleware, MiddlewareContext
from fastmcp.server.dependencies import get_http_headers
from fastmcp.exceptions import ToolError

from database import init_db, index_directory, git_pull_from_remote
import tools

# Load environment variables from .env file
load_dotenv()

# Initialize the MCP server
mcp = FastMCP("Knowledge Base")

KB_DIR = os.getenv("KB_DIR")
DB_PATH = os.getenv("KB_DB")
AUTH_TOKEN = os.getenv("AUTH_TOKEN")

if not KB_DIR or not DB_PATH:
    raise ValueError("KB_DIR and KB_DB must be set in .env file")


# Optional Bearer token authentication for SSE mode
class BearerAuthMiddleware(Middleware):
    """Validate Bearer token for all tool calls in SSE mode."""

    def __init__(self, token: str):
        self.token = token

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        headers = get_http_headers() or {}
        auth_header = headers.get("authorization", "")

        # Check for valid Bearer token
        if not auth_header.startswith("Bearer "):
            raise ToolError("Missing or invalid Authorization header. Expected: Bearer <token>")

        if auth_header[7:] != self.token:
            raise ToolError("Invalid authentication token")

        return await call_next(context)


if AUTH_TOKEN:
    mcp.add_middleware(BearerAuthMiddleware(AUTH_TOKEN))
    print("Authentication enabled for SSE mode", file=sys.stderr)


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
async def sync_from_git(ctx: Context) -> str:
    """
    Pull latest changes from Git and reindex the knowledge base.

    Use this after making changes on other devices (iOS app, local machine, etc.)
    to sync those changes to the Railway-hosted MCP server.

    Returns:
        Status message with git pull result and reindex statistics
    """
    return await tools.sync_from_git(KB_DIR, DB_PATH, ctx)


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
        ctx:
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
        ctx:
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
        ctx:
        filepath: Full path to the note file
        content: Content to append to the note

    Returns:
        Confirmation message
    """
    return await tools.append_to_note(filepath, content, DB_PATH, ctx)


@mcp.tool
async def create_directory(directory_path: str, ctx: Context = None) -> str:
    """
    Create a directory within the knowledge base.

    Args:
        ctx:
        directory_path: Relative path for the directory to create (e.g., "projects/python")

    Returns:
        Confirmation message
    """
    return await tools.create_kb_directory(directory_path, KB_DIR, ctx)


@mcp.tool
async def what_should_i_do(user_request: str) -> str:
    """
    SMALL MODEL HELPER: Not sure which tool to use? Describe what you want to do.

    This tool helps choose the right tool for your task. Just describe your intent.

    Examples:
    - "I want to jot down some quick thoughts" → suggests create_note
    - "What have I been working on lately?" → suggests list_recent_notes
    - "Where did I write about databases?" → suggests search_notes
    - "Add more info to my meeting notes" → suggests append_to_note
    - "How many notes do I have?" → suggests get_kb_stats
    - "I edited files externally" → suggests reindex_kb
    - "Organize notes into folders" → suggests create_directory
    - "Rewrite my old note completely" → suggests update_note
    - "Show me that Python tutorial" → suggests read_note

    Args:
        user_request: Describe what you want to do in plain language

    Returns:
        Recommended tool name and instructions on how to use it
    """
    return await tools.what_should_i_do_tool(user_request, DB_PATH)


@mcp.tool
async def quick_search(keywords: str) -> str:
    """
    SMALL MODEL: Lightweight search - returns only titles and paths (no content snippets).
    Use this to save tokens when you just need to find which notes exist.

    Args:
        keywords: Search keywords (space-separated)

    Returns:
        Compact list of top 5 matching notes
    """
    return await tools.quick_search_tool(keywords, DB_PATH)


@mcp.tool
async def get_note_summary(filepath: str) -> str:
    """
    SMALL MODEL: Get brief summary of a note (saves tokens vs reading full content).
    Use this to check if a note is relevant before calling read_note.

    Args:
        filepath: Full path to the note file

    Returns:
        Brief summary with key topics
    """
    return await tools.get_summary_tool(filepath, DB_PATH)


# Initialize on startup
init_db(DB_PATH)

# Initialize tool prompts for small LLM support
try:
    from database import populate_tool_prompts
    populate_tool_prompts(DB_PATH)
    print("Tool prompts initialized for small LLM support", file=sys.stderr)
except Exception as e:
    print(f"Warning: Could not initialize tool prompts: {e}", file=sys.stderr)

# Ensure KB_DIR exists (needed for Railway/cloud deployments with empty volumes)
Path(KB_DIR).mkdir(parents=True, exist_ok=True)

if Path(KB_DIR).exists():
    # Pull from remote to sync changes from other machines
    success, git_message = git_pull_from_remote(KB_DIR)
    if success:
        print(f"Git sync: {git_message}", file=sys.stderr)
    else:
        print(f"Git sync warning: {git_message}", file=sys.stderr)

    # Index all files
    indexed_count, removed_count = index_directory(KB_DIR, DB_PATH)
    if removed_count > 0:
        print(f"Indexed {indexed_count} notes and removed {removed_count} orphaned entries from {KB_DIR}", file=sys.stderr)
    else:
        print(f"Indexed {indexed_count} notes from {KB_DIR}", file=sys.stderr)

if __name__ == "__main__":
    # Read transport configuration from environment
    transport = os.getenv("MCP_TRANSPORT", "stdio")
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))

    # Debug: show transport configuration
    print(f"Transport config: MCP_TRANSPORT={transport}, HOST={host}, PORT={port}", file=sys.stderr)

    try:
        if transport == "sse":
            print(f"Starting SSE server on {host}:{port}", file=sys.stderr)
            mcp.run(transport="sse", host=host, port=port)
        else:
            mcp.run(transport="stdio")
    except KeyboardInterrupt:
        print("\nShutting down gracefully...", file=sys.stderr)
        sys.exit(0)
