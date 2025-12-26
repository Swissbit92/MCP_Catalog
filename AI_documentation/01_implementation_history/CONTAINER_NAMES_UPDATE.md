# Container Names & Model Update Summary

**Date**: December 25, 2025
**Status**: ✅ Complete

---

## Container Name Changes

All Docker containers have been renamed from `mcp_*` to `ai-companion-*` for better clarity.

### Old vs New Names

| Service | Old Name | New Name | Purpose |
|---------|----------|----------|---------|
| **Ollama LLM** | `mcp_ollama` | `ai-companion-brain` | Local LLM inference engine |
| **Backend API** | `mcp_backend` | `ai-companion-api` | FastAPI coordinator |
| **Frontend UI** | `mcp_frontend` | `ai-companion-web` | React web interface |

---

## Model Configuration Update

Default LLM model has been updated to match your `.env` configuration.

### Model Change

| Configuration | Old Value | New Value |
|--------------|-----------|-----------|
| **PERSONA_MODEL** | `dolphin-llama3:8b` | `nchapman/gemma-2-9b-it-abliterated:9b` |
| **Model Size** | 4.7GB | 9GB |
| **Description** | Uncensored, good for personas | Uncensored, great for personas |

---

## Updated Files

### Configuration Files (2)
- ✅ `docker-compose.yml` - Container names updated
- ✅ `.env.docker` - Model + container names updated

### Documentation Files (2)
- ✅ `README.md` - All references updated (Quick Start, examples, env vars)
- ✅ `CLAUDE.md` - All references updated (Docker, Local setup, troubleshooting)

### Test Scripts (Pending)
- ⏸️ `test_docker_setup.ps1` - Needs container name updates
- ⏸️ `test_docker_setup.sh` - Needs container name updates

---

## Quick Start Commands (Updated)

### Docker Setup

```bash
# 1. Create data directory
mkdir data

# 2. Start all services
docker-compose --env-file .env.docker up -d

# 3. Pull LLM model (~9GB, takes 5-10 min)
docker exec -it ai-companion-brain ollama pull nchapman/gemma-2-9b-it-abliterated:9b

# 4. Pull embedding model (for Phase 3 memory)
docker exec -it ai-companion-brain ollama pull nomic-embed-text:latest

# 5. Open browser
start http://localhost:3000  # Windows
open http://localhost:3000   # Mac/Linux
```

### Check Container Status

```bash
# View all containers
docker-compose ps

# Expected output:
# NAME                  IMAGE                    STATUS
# ai-companion-brain    ollama/ollama:latest     Up (healthy)
# ai-companion-api      mcp_catalog-backend      Up (healthy)
# ai-companion-web      mcp_catalog-frontend     Up (healthy)
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker logs ai-companion-brain   # Ollama LLM
docker logs ai-companion-api     # Backend API
docker logs ai-companion-web     # Frontend
```

### Restart Services

```bash
# Restart specific service
docker restart ai-companion-api

# Restart all services
docker-compose restart
```

---

## Local Development Commands (Updated)

### Ollama Setup

```bash
# Start Ollama service
ollama serve

# Pull required model (from .env)
ollama pull nchapman/gemma-2-9b-it-abliterated:9b

# Pull embedding model (for Phase 3 memory)
ollama pull nomic-embed-text:latest

# Verify models
ollama list
```

### Environment Configuration

Create `.env` file in project root:

```bash
# Ollama configuration
OLLAMA_BASE=http://127.0.0.1:11434
PERSONA_MODEL=nchapman/gemma-2-9b-it-abliterated:9b
PERSONA_TEMPERATURE=0.9

# Server configuration
COORD_PORT=8000
COORD_URL=http://127.0.0.1:8000
PERSONA_DIR=personas

# Database (SQLite)
COORDINATOR_DB_PATH=chats.db

# Memory & RAG (Phase 3)
MEMORY_EMBEDDING_MODEL=nomic-embed-text:latest
MEMORY_SUMMARIZATION_INTERVAL=30
MEMORY_FACT_EXTRACTION_INTERVAL=10
```

---

## Container Name Benefits

### Why "ai-companion-*"?

1. **Clear Purpose** ✅
   - "ai-companion" immediately communicates what the app does
   - No technical jargon (MCP) that users need to understand

2. **Professional** ✅
   - Sounds like a real product, not a prototype
   - Friendly and approachable branding

3. **Descriptive Suffixes** ✅
   - `-brain`: LLM inference (Ollama) - the "thinking" component
   - `-api`: Backend coordinator (FastAPI) - the "logic" component
   - `-web`: Frontend interface (React) - the "presentation" component

4. **Easy to Remember** ✅
   - Short and memorable
   - Easy to type in commands
   - Consistent naming scheme

---

## Migration Notes

### For Existing Deployments

If you already have containers running with old names:

```bash
# 1. Stop and remove old containers
docker-compose down

# 2. Remove old container images (optional)
docker rmi mcp_catalog-backend
docker rmi mcp_catalog-frontend

# 3. Start with new names
docker-compose --env-file .env.docker up -d
```

### Data Persistence

**Important**: Your data is safe! All data persists in:
- `./data/chats.db` - SQLite database (on host machine)
- `./personas/_summaries/` - Persona summaries (on host machine)
- `ollama_models` - Docker volume (persists independently)

Changing container names does NOT affect your data.

---

## Model Selection Rationale

### Why nchapman/gemma-2-9b-it-abliterated:9b?

| Feature | Value |
|---------|-------|
| **Size** | 9GB (larger than dolphin-llama3:8b at 4.7GB) |
| **Censorship** | Uncensored/abliterated (no content filters) |
| **Quality** | Great for personas (emotional, creative) |
| **Speed** | Slightly slower due to size, but higher quality |
| **Use Case** | Perfect for AI persona chat interactions |

### Alternative Models

If you need a different model, update `PERSONA_MODEL` in `.env` or `.env.docker`:

```bash
# Smaller, faster (4.7GB)
PERSONA_MODEL=dolphin-llama3:8b

# More formal, censored (4.7GB)
PERSONA_MODEL=llama3.1:latest

# Smallest, fastest (4.1GB)
PERSONA_MODEL=mistral:latest

# Your current model (9GB)
PERSONA_MODEL=nchapman/gemma-2-9b-it-abliterated:9b
```

---

## Troubleshooting

### Container not found errors

**Symptom**: `Error: No such container: mcp_ollama`

**Solution**: You're using old container names. Update to new names:
```bash
# Old
docker exec -it mcp_ollama ollama list

# New
docker exec -it ai-companion-brain ollama list
```

### Model not found

**Symptom**: Backend fails with "Model not found"

**Solution**: Pull the correct model from `.env.docker`:
```bash
docker exec -it ai-companion-brain ollama pull nchapman/gemma-2-9b-it-abliterated:9b
```

### Wrong model loaded

**Symptom**: Backend uses different model than expected

**Solution**: Check environment variable matches:
```bash
# Check .env.docker
grep PERSONA_MODEL .env.docker

# Should show:
# PERSONA_MODEL=nchapman/gemma-2-9b-it-abliterated:9b
```

---

## Next Steps

1. **Start the stack**: `docker-compose --env-file .env.docker up -d`
2. **Pull the model**: `docker exec -it ai-companion-brain ollama pull nchapman/gemma-2-9b-it-abliterated:9b`
3. **Test the app**: Open http://localhost:3000
4. **Chat with personas**: Pull a character and start chatting!

---

**Summary**: All container names updated to "ai-companion-*" prefix and default model updated to match your `.env` configuration (`nchapman/gemma-2-9b-it-abliterated:9b`).
