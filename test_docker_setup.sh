#!/bin/bash
# =============================================================================
# MCP Coordinator - Docker Setup Test Script
# =============================================================================
# Tests that Docker Compose stack is running correctly with SQLite
#
# Usage:
#   chmod +x test_docker_setup.sh
#   ./test_docker_setup.sh
# =============================================================================

set -e  # Exit on error

echo "=========================================="
echo "MCP Coordinator Docker Setup Test"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

pass() {
    echo -e "${GREEN}✓${NC} $1"
}

fail() {
    echo -e "${RED}✗${NC} $1"
    exit 1
}

warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Check if Docker is running
echo "1. Checking Docker..."
if ! docker ps > /dev/null 2>&1; then
    fail "Docker is not running. Please start Docker Desktop."
fi
pass "Docker is running"
echo ""

# Check if docker-compose.yml exists
echo "2. Checking docker-compose.yml..."
if [ ! -f "docker-compose.yml" ]; then
    fail "docker-compose.yml not found. Are you in the project root?"
fi
pass "docker-compose.yml found"
echo ""

# Check if .env.docker exists
echo "3. Checking .env.docker..."
if [ ! -f ".env.docker" ]; then
    warn ".env.docker not found (optional, will use defaults)"
else
    pass ".env.docker found"
fi
echo ""

# Check if data directory exists
echo "4. Checking data directory..."
if [ ! -d "data" ]; then
    echo "Creating data directory..."
    mkdir -p data
    pass "Created data directory"
else
    pass "Data directory exists"
fi
echo ""

# Check if containers are running
echo "5. Checking running containers..."
if ! docker-compose ps | grep -q "Up"; then
    warn "Containers not running. Starting stack..."
    docker-compose --env-file .env.docker up -d
    echo "Waiting for services to start (30 seconds)..."
    sleep 30
fi

# Check individual services
echo ""
echo "6. Checking service health..."

# Check Ollama
if docker-compose ps | grep mcp_ollama | grep -q "Up"; then
    pass "Ollama container is running"
else
    fail "Ollama container is not running"
fi

# Check Backend
if docker-compose ps | grep mcp_backend | grep -q "Up"; then
    pass "Backend container is running"
else
    fail "Backend container is not running"
fi

# Check Frontend
if docker-compose ps | grep mcp_frontend | grep -q "Up"; then
    pass "Frontend container is running"
else
    fail "Frontend container is not running"
fi
echo ""

# Check if services are healthy
echo "7. Checking service health status..."
sleep 5  # Give health checks time to run

# Check backend health endpoint
echo "Checking backend health endpoint..."
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    pass "Backend health check passed"
else
    warn "Backend health check failed (may still be starting up)"
    echo "   Waiting 30 more seconds..."
    sleep 30
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        pass "Backend health check passed (after wait)"
    else
        fail "Backend health check failed"
    fi
fi
echo ""

# Check frontend
echo "Checking frontend..."
if curl -f http://localhost:3000 > /dev/null 2>&1; then
    pass "Frontend is accessible"
else
    warn "Frontend not accessible yet (may still be building)"
fi
echo ""

# Check Ollama
echo "Checking Ollama..."
if docker exec mcp_ollama ollama list > /dev/null 2>&1; then
    pass "Ollama is responsive"

    # Check if model is pulled
    if docker exec mcp_ollama ollama list | grep -q "dolphin-llama3:8b"; then
        pass "Model 'dolphin-llama3:8b' is available"
    elif docker exec mcp_ollama ollama list | grep -q "llama3.1"; then
        pass "Model 'llama3.1:latest' is available"
    else
        warn "No LLM model found"
        echo "   Run: docker exec -it mcp_ollama ollama pull dolphin-llama3:8b"
    fi
else
    fail "Ollama is not responsive"
fi
echo ""

# Check data persistence
echo "8. Checking data persistence..."
if [ -f "data/chats.db" ]; then
    pass "SQLite database exists (data/chats.db)"
    SIZE=$(du -h data/chats.db | cut -f1)
    echo "   Database size: $SIZE"
else
    warn "SQLite database not created yet (normal for first run)"
fi
echo ""

# Check persona summaries
echo "9. Checking persona files..."
if [ -d "personas" ]; then
    PERSONA_COUNT=$(ls -1 personas/*.json 2>/dev/null | wc -l)
    pass "Found $PERSONA_COUNT persona files"

    if [ -d "personas/_summaries" ]; then
        SUMMARY_COUNT=$(ls -1 personas/_summaries/*.json 2>/dev/null | wc -l)
        if [ $SUMMARY_COUNT -gt 0 ]; then
            pass "Found $SUMMARY_COUNT persona summaries (cache)"
        else
            warn "No persona summaries yet (will be auto-generated)"
        fi
    fi
else
    fail "Personas directory not found"
fi
echo ""

# Test API endpoint
echo "10. Testing API endpoints..."
if curl -s http://localhost:8000/health | grep -q "ok"; then
    pass "Health endpoint returns 'ok'"

    # Try to get personas
    if curl -s http://localhost:8000/personas | grep -q "personas"; then
        pass "Personas endpoint working"
    else
        warn "Personas endpoint returned unexpected response"
    fi
else
    fail "Health endpoint not returning 'ok'"
fi
echo ""

# Final summary
echo "=========================================="
echo "Test Summary"
echo "=========================================="
pass "Docker Compose stack is running"
pass "All core services are operational"
echo ""
echo "Next steps:"
echo "1. Open http://localhost:3000 in your browser"
echo "2. Pull an LLM model if not done:"
echo "   docker exec -it mcp_ollama ollama pull dolphin-llama3:8b"
echo "3. Start chatting with personas!"
echo ""
echo "Useful commands:"
echo "  - View logs: docker-compose logs -f"
echo "  - Restart: docker-compose restart"
echo "  - Stop: docker-compose down"
echo "  - Backup: cp data/chats.db data/chats.db.backup"
echo ""
echo "=========================================="
