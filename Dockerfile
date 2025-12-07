# Use Python 3.11 slim image for smaller size
FROM python:3.11-slim

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

# Set default environment variables
ENV KB_DIR=/data/notes
ENV KB_DB=/data/db/kb_index.db
ENV LOG_LEVEL=INFO

# Expose any ports if needed (MCP typically uses stdio, but keeping for flexibility)
# EXPOSE 8000

# Run the server
CMD ["python", "server.py"]
