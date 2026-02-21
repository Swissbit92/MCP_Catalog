#!/bin/bash
# =============================================================================
# AI Companion - Docker Setup Script (Linux/Mac)
# =============================================================================
# One-command setup for AI Companion with Docker
#
# Usage:
#   chmod +x setup-docker.sh
#   ./setup-docker.sh
# =============================================================================

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo ""
echo "════════════════════════════════════════════════════════════"
echo "           🐳 AI Companion - Docker Setup"
echo "════════════════════════════════════════════════════════════"
echo ""

# Check if Docker is running
echo -e "${BLUE}🔍 Checking Docker...${NC}"
if ! docker ps > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Docker is not running. Please start Docker Desktop first.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker is running${NC}"
echo ""

# Check if docker-compose.yml exists
if [ ! -f "docker-compose.yml" ]; then
    echo -e "${YELLOW}⚠️  docker-compose.yml not found. Are you in the project root?${NC}"
    exit 1
fi

# Step 1: Start Docker containers
echo -e "${BLUE}📦 Starting Docker containers...${NC}"
echo "   This will download images (~2GB) on first run"
echo ""
docker-compose --env-file .env.docker up -d

if [ $? -ne 0 ]; then
    echo -e "${YELLOW}⚠️  Failed to start containers. Check the error above.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Containers started${NC}"
echo ""

# Step 2: Wait for Ollama to be ready
echo -e "${BLUE}⏳ Waiting for Ollama to be ready...${NC}"
sleep 10

# Check if Ollama is responsive
for i in {1..6}; do
    if docker exec ai-companion-brain ollama list > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Ollama is ready${NC}"
        break
    fi
    if [ $i -eq 6 ]; then
        echo -e "${YELLOW}⚠️  Ollama is taking longer than expected. Continuing anyway...${NC}"
    else
        echo "   Waiting... (attempt $i/6)"
        sleep 5
    fi
done
echo ""

# Step 3: Pull main LLM model
echo -e "${BLUE}🧠 Pulling AI model (9GB download, this will take 5-10 minutes)${NC}"
echo "   Model: nchapman/gemma-2-9b-it-abliterated:9b"
echo ""
docker exec -it ai-companion-brain ollama pull nchapman/gemma-2-9b-it-abliterated:9b

if [ $? -ne 0 ]; then
    echo ""
    echo -e "${YELLOW}⚠️  Model download failed or was interrupted.${NC}"
    echo "   You can retry manually:"
    echo "   docker exec -it ai-companion-brain ollama pull nchapman/gemma-2-9b-it-abliterated:9b"
    exit 1
fi
echo ""
echo -e "${GREEN}✓ Main model downloaded${NC}"
echo ""

# Step 4: Pull embedding model (for Phase 3 memory features)
echo -e "${BLUE}📚 Pulling embedding model (for memory features, ~274MB)${NC}"
echo "   Model: nomic-embed-text:latest"
echo ""
docker exec -it ai-companion-brain ollama pull nomic-embed-text:latest

if [ $? -ne 0 ]; then
    echo ""
    echo -e "${YELLOW}⚠️  Embedding model download failed. This is optional for basic usage.${NC}"
    echo "   You can retry manually later:"
    echo "   docker exec -it ai-companion-brain ollama pull nomic-embed-text:latest"
fi
echo ""

# Step 5: Verify all services are running
echo -e "${BLUE}🔍 Verifying services...${NC}"
sleep 3

SERVICES_OK=true

# Check Ollama
if docker exec ai-companion-brain ollama list > /dev/null 2>&1; then
    echo -e "${GREEN}✓ ai-companion-brain (Ollama LLM)${NC}"
else
    echo -e "${YELLOW}⚠ ai-companion-brain (not responding)${NC}"
    SERVICES_OK=false
fi

# Check Backend
if curl -f http://localhost:8000/ready > /dev/null 2>&1; then
    echo -e "${GREEN}✓ ai-companion-api (Backend)${NC}"
else
    echo -e "${YELLOW}⚠ ai-companion-api (not ready yet)${NC}"
    SERVICES_OK=false
fi

# Check Frontend
if curl -f http://localhost:3000 > /dev/null 2>&1; then
    echo -e "${GREEN}✓ ai-companion-web (Frontend)${NC}"
else
    echo -e "${YELLOW}⚠ ai-companion-web (not ready yet)${NC}"
    SERVICES_OK=false
fi

echo ""

# Final message
if [ "$SERVICES_OK" = true ]; then
    echo "════════════════════════════════════════════════════════════"
    echo -e "${GREEN}✅ Setup complete!${NC}"
    echo "════════════════════════════════════════════════════════════"
    echo ""
    echo "🌐 Your AI Companion is ready at:"
    echo ""
    echo "   Frontend:  http://localhost:3000"
    echo "   Backend:   http://localhost:8000"
    echo "   API Docs:  http://localhost:8000/docs"
    echo ""
    echo "📝 Next steps:"
    echo "   1. Open http://localhost:3000 in your browser"
    echo "   2. Pull a character from the gacha"
    echo "   3. Start chatting with your AI personas!"
    echo ""
    echo "💡 Useful commands:"
    echo "   View logs:     docker-compose logs -f"
    echo "   Stop services: docker-compose down"
    echo "   Restart:       docker-compose restart"
    echo ""
else
    echo "════════════════════════════════════════════════════════════"
    echo -e "${YELLOW}⚠️  Setup completed with warnings${NC}"
    echo "════════════════════════════════════════════════════════════"
    echo ""
    echo "Some services may still be starting up. Wait 30 seconds and try:"
    echo "   curl http://localhost:8000/health"
    echo "   curl http://localhost:3000"
    echo ""
    echo "View logs to troubleshoot:"
    echo "   docker-compose logs -f"
    echo ""
fi

# Step 6: Run post-startup verification
echo ""
echo -e "${BLUE}🔍 Running post-startup verification...${NC}"
if command -v python3 &> /dev/null; then
    python3 scripts/docker/verify_startup.py --skip-queries
elif command -v python &> /dev/null; then
    python scripts/docker/verify_startup.py --skip-queries
else
    echo -e "${YELLOW}⚠ Python not found — skipping automated verification${NC}"
    echo "   You can run it manually: python scripts/docker/verify_startup.py"
fi
