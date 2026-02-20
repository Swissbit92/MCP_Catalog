# =============================================================================
# MCP Coordinator - Backend Dockerfile (SQLite Edition)
# =============================================================================
# Optimized for local personal use with SQLite database
# For production PostgreSQL setup, see PRODUCTION_READINESS_PLAN.md
# =============================================================================

FROM python:3.11-slim

# Metadata
LABEL maintainer="MCP Coordinator"
LABEL description="FastAPI backend for AI persona chat with SQLite"
LABEL version="1.0.0-sqlite"

# Set working directory
WORKDIR /app

# Install system dependencies
# - curl: health checks
# - git: some Python packages require it
# - Docker CLI: for spawning MCP server containers (Brave Search, MongoDB)
RUN apt-get update && apt-get install -y \
    curl \
    git \
    ca-certificates \
    gnupg \
    lsb-release \
    && rm -rf /var/lib/apt/lists/*

# Install Docker CLI for MCP container spawning
RUN mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg \
    && echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian \
      $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null \
    && apt-get update \
    && apt-get install -y docker-ce-cli \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip cache purge

# Copy application code
COPY src/ ./src/
COPY personas/ ./personas/

# Copy Alembic migrations for database schema management
COPY alembic/ ./alembic/
COPY alembic.ini .

# Copy strategies directory (for Jupiter autonomous trading)
COPY strategies/ ./strategies/

# Create directories for SQLite database and logs
# These will be mounted as volumes from host
RUN mkdir -p /app/data /app/logs

# Create non-root user for security
# NOTE: Running as root to allow Docker socket access for MCP containers
# In production, use Docker group permissions instead
RUN useradd -m -u 1000 coordinator && \
    chown -R coordinator:coordinator /app

# Switch to non-root user
# DISABLED: Need root for Docker socket access (MCP container spawning)
# USER coordinator

# Health check - verifies backend is responding
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Run the server
# Note: --reload is enabled for development convenience
# For production, remove --reload and use gunicorn
CMD ["uvicorn", "src.coordinator.server:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--log-level", "info"]
