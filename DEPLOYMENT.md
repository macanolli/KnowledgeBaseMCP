# Cloud Deployment Guide

This guide covers deploying the Knowledge Base MCP server to cloud platforms for remote access.

## Overview

The server supports two transport modes:
- **STDIO** (default): For local Claude Desktop integration
- **SSE** (HTTP): For remote cloud deployments

When deployed remotely, optional Bearer token authentication protects your knowledge base.

## Railway Deployment

### 1. Prerequisites

- [Railway account](https://railway.app)
- Git repository with this code
- Your notes in a Git repository (recommended for persistence)

### 2. Create Railway Project

1. Log into Railway and click **New Project**
2. Select **Deploy from GitHub repo**
3. Choose your Knowledge Base MCP repository
4. Railway will auto-detect Python and create a service

### 3. Configure Environment Variables

In Railway's service settings, add these variables:

| Variable | Value | Required |
|----------|-------|----------|
| `KB_DIR` | `/app/notes` | Yes |
| `KB_DB` | `/app/data/.kb_index.db` | Yes |
| `MCP_TRANSPORT` | `sse` | Yes |
| `PORT` | `${{PORT}}` | Yes (Railway provides) |
| `HOST` | `0.0.0.0` | Yes |
| `AUTH_TOKEN` | `<your-secure-token>` | Recommended |
| `GIT_TOKEN` | `<github-pat>` | Optional (for git sync) |

#### Generate a Secure Auth Token

```bash
openssl rand -hex 32
```

Copy the output and use it as your `AUTH_TOKEN`.

### 4. Notes Storage Options

**Option A: Embedded in Repository**
- Put your notes in a `notes/` directory in the repo
- Set `KB_DIR=/app/notes`

**Option B: Railway Volume (Persistent)**
1. Add a Volume to your Railway service
2. Mount it at `/app/data`
3. Set `KB_DIR=/app/data/notes`
4. Set `KB_DB=/app/data/.kb_index.db`

**Option C: Clone from Git on Startup**
- Create a startup script that clones your notes repo
- Set `GIT_TOKEN` for private repos

### 5. Deploy

Railway auto-deploys on git push. Check logs for:
```
Authentication enabled for SSE mode
Indexed X notes from /app/notes
```

### 6. Get Your Endpoint URL

Railway provides a URL like: `https://your-app.up.railway.app`

Your SSE endpoint will be: `https://your-app.up.railway.app/sse`

## Claude Desktop Configuration

Add the remote server to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "knowledge-base-remote": {
      "command": "npx",
      "args": [
        "mcp-remote",
        "https://your-app.up.railway.app/sse",
        "--header",
        "Authorization: Bearer YOUR_AUTH_TOKEN"
      ]
    }
  }
}
```

**Note**: Install mcp-remote globally first: `npm install -g mcp-remote`

## Security Best Practices

### Authentication
- **Always set AUTH_TOKEN** for remote deployments
- Use a strong, randomly generated token (32+ hex characters)
- Never commit tokens to git - use environment variables

### Network Security
- Railway provides HTTPS by default
- Consider IP allowlisting if your platform supports it
- Use private networking between services when possible

### Data Security
- Your notes are stored on the server - consider sensitivity
- Use Railway Volumes for persistent storage
- Regular backups recommended for important data

### Token Rotation
1. Generate a new token: `openssl rand -hex 32`
2. Update `AUTH_TOKEN` in Railway
3. Update your Claude Desktop config
4. Restart Claude Desktop

## Troubleshooting

### Connection Refused
- Verify `HOST=0.0.0.0` (not `127.0.0.1`)
- Check `MCP_TRANSPORT=sse`
- Confirm PORT matches Railway's assigned port

### Authentication Errors
- Verify token matches exactly (no extra spaces)
- Check header format: `Authorization: Bearer <token>`
- Ensure AUTH_TOKEN is set in Railway environment

### Notes Not Found
- Verify `KB_DIR` path exists
- Check Railway logs for indexing output
- Ensure notes have `.md` extension

### mcp-remote Issues
- Update to latest: `npm update -g mcp-remote`
- Check Node.js version (18+ recommended)
- Try with `--debug` flag for verbose output

## Other Cloud Platforms

The server is cloud-agnostic. Key requirements for any platform:

1. **Python 3.11+** runtime
2. **Environment variables** support
3. **HTTP/HTTPS** ingress
4. **Persistent storage** (for notes and database)

### Platform-Specific Notes

**Render**: Use `render.yaml` for configuration
**Fly.io**: Use `fly.toml`, set `internal_port` to match PORT
**Heroku**: Use `Procfile`: `web: python server.py`
**Docker**: See Dockerfile in repository (if available)

## Local SSE Testing

Test SSE mode locally before deploying:

```bash
# Set environment
export MCP_TRANSPORT=sse
export PORT=3399
export AUTH_TOKEN=test-token-123

# Run server
python server.py

# Test endpoint (in another terminal)
curl -H "Authorization: Bearer test-token-123" \
     http://localhost:3399/sse
```
