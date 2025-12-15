# Use Python 3.11 slim image for smaller size
FROM python:3.11-slim

# Install git and openssh-client for git operations
RUN apt-get update && \
    apt-get install -y --no-install-recommends git openssh-client && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY server.py .
COPY database.py .
COPY tools.py .
COPY .env.example .

# Create directories for notes and database
RUN mkdir -p /data/notes /data/db

# Create SSH directory and configure git to disable strict host key checking
RUN mkdir -p /root/.ssh && \
    chmod 700 /root/.ssh && \
    ssh-keyscan github.com > /root/.ssh/known_hosts 2>/dev/null && \
    git config --global core.sshCommand "ssh -o StrictHostKeyChecking=accept-new"

# Set default environment variables
ENV KB_DIR=/data/notes
ENV KB_DB=/data/db/kb_index.db
ENV LOG_LEVEL=INFO

# Expose any ports if needed (MCP typically uses stdio, but keeping for flexibility)
# EXPOSE 8000

# Run the server
CMD ["python", "server.py"]
