# Docker Troubleshooting Guide

This guide covers common Docker issues and how to fix them using the automated troubleshooting scripts.

## Quick Reference

| Issue | Solution |
|-------|----------|
| Orphaned network errors | `.\fix-docker-network.ps1` or `.\fix-docker-network.bat` |
| Containers won't start | `.\fix-docker-network.ps1 -Quick` |
| Persistent issues | `.\fix-docker-network.ps1 -Nuclear` |
| Check current status | `.\fix-docker-network.ps1 -Verify` |

## Common Issues

### 1. Orphaned Network Errors

**Symptoms:**
```
Error: network f708feda4bed... not found
Cannot start Docker Compose application
```

**Cause:** Docker daemon restarted or containers stopped improperly, leaving stale network references.

**Fix:**
```powershell
# Automated fix (recommended)
.\fix-docker-network.ps1

# Or simple batch version
.\fix-docker-network.bat

# Manual fix
docker-compose down
docker network prune -f
docker-compose --env-file .env.docker up -d
```

### 2. Containers Won't Start

**Symptoms:**
- Containers stuck in "Starting" state
- Health checks failing
- Services unreachable

**Fix:**
```powershell
# Quick fix (stops, cleans, restarts)
.\fix-docker-network.ps1 -Quick

# If that doesn't work, try nuclear option
.\fix-docker-network.ps1 -Nuclear
```

### 3. Data Loss Concerns

**Q: Will these scripts delete my data?**

**A: No.** Your data is safe because:
- SQLite database is in `./data/chats.db` on your host (persists across container deletions)
- Ollama models are in a Docker volume (not deleted by scripts)
- Persona summaries are in `./personas/_summaries/` on your host

The scripts only remove:
- Container instances (can be recreated)
- Network configurations (auto-recreated)
- Image cache (only with `-Nuclear` option)

## Troubleshooting Scripts

### fix-docker-network.ps1 (PowerShell)

**Features:**
- Color-coded output
- Detailed diagnostics
- Health check verification
- Multiple fix modes

**Usage:**
```powershell
# Quick fix (default)
.\fix-docker-network.ps1
.\fix-docker-network.ps1 -Quick

# Full rebuild (removes everything, rebuilds from scratch)
.\fix-docker-network.ps1 -Nuclear

# Verify status without making changes
.\fix-docker-network.ps1 -Verify
```

**What it does:**
1. ✅ Checks Docker is running
2. ✅ Verifies docker-compose.yml exists
3. ✅ Shows current container/network status
4. ✅ Executes fix (Quick or Nuclear)
5. ✅ Validates all services are healthy
6. ✅ Provides access URLs

### fix-docker-network.bat (Batch)

**Features:**
- Simple one-click fix
- No parameters needed
- Works on all Windows versions

**Usage:**
```batch
# Double-click the file, or run from command prompt
.\fix-docker-network.bat
```

**What it does:**
1. Stops all containers
2. Cleans orphaned networks
3. Restarts services
4. Waits for health checks
5. Shows container status

## Fix Comparison

| Mode | Speed | Data Loss | When to Use |
|------|-------|-----------|-------------|
| **Quick** | ~60s | None | First attempt, most issues |
| **Nuclear** | ~5min | None* | Persistent issues, corrupted state |
| **Verify** | ~10s | None | Just check status |

*Nuclear rebuilds images but preserves data volumes

## Verification Steps

After running a fix, verify services are working:

```powershell
# Check container status
docker-compose ps

# Test backend health
curl http://localhost:8000/health

# Test frontend (browser)
start http://localhost:3000

# View logs if issues persist
docker-compose logs -f backend
```

## Prevention

**Best Practices:**
1. ✅ Always use `docker-compose down` to stop services (not Docker Desktop UI)
2. ✅ Let Docker Desktop fully start before starting containers
3. ✅ Avoid force-quitting Docker Desktop while containers are running
4. ✅ Use automated scripts for maintenance

**Stopping Services Properly:**
```powershell
# Good - clean shutdown
docker-compose down

# Avoid - can leave orphaned networks
# Manually stopping containers in Docker Desktop UI
```

## Advanced Troubleshooting

### View Detailed Logs

```powershell
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f ollama
docker-compose logs -f frontend

# Last 100 lines
docker-compose logs --tail=100 backend
```

### Inspect Network

```powershell
# List all networks
docker network ls

# Inspect MCP network
docker network inspect mcp_catalog_mcp-network

# Find orphaned networks
docker network ls --filter "dangling=true"
```

### Container Diagnostics

```powershell
# Check container health
docker inspect ai-companion-api --format='{{.State.Health.Status}}'

# View resource usage
docker stats

# Enter container shell
docker exec -it ai-companion-api bash
```

### Complete Reset (Nuclear Option)

If all else fails, complete reset:

```powershell
# 1. Stop everything
docker-compose down -v

# 2. Remove all MCP containers and images
docker rm -f ai-companion-brain ai-companion-api ai-companion-web
docker rmi mcp_catalog-backend mcp_catalog-frontend

# 3. Clean Docker system
docker system prune -a -f
docker volume prune -f
docker network prune -f

# 4. Rebuild from scratch
docker-compose --env-file .env.docker up -d --build
```

**⚠️ Warning:** This removes Ollama models. You'll need to re-pull them:
```powershell
docker exec -it ai-companion-brain ollama pull nchapman/gemma-2-9b-it-abliterated:9b
docker exec -it ai-companion-brain ollama pull nomic-embed-text:latest
```

## Getting Help

If issues persist after trying these solutions:

1. Check logs: `docker-compose logs -f`
2. Verify Docker version: `docker --version` (requires 20.10+)
3. Check Docker Desktop settings:
   - Resources → Advanced → Memory (minimum 8GB recommended)
   - General → "Use Docker Compose V2" should be enabled
4. Review CLAUDE.md "Common Troubleshooting" section
5. Check GitHub issues: https://github.com/anthropics/claude-code/issues

## Script Details

### Exit Codes

Both scripts use standard exit codes:
- `0` - Success
- `1` - Error (Docker not running, docker-compose.yml not found, services failed to start)

### Requirements

- Windows 10/11
- Docker Desktop installed and running
- PowerShell 5.1+ (for .ps1 script)
- Project directory: `MCP_Catalog`

### Files Modified

The scripts do **NOT** modify:
- ❌ Your code files
- ❌ SQLite database (`./data/chats.db`)
- ❌ Persona definitions (`./personas/*.json`)
- ❌ Persona summaries (`./personas/_summaries/`)
- ❌ Environment variables (`.env.docker`)

The scripts **DO** modify:
- ✅ Container instances (stopped/recreated)
- ✅ Network configurations (cleaned/recreated)
- ✅ Docker images (only with `-Nuclear` option)

## Reference

For more information, see:
- `CLAUDE.md` - Full project documentation
- `DOCKER_QUICKSTART.md` - Docker setup guide
- `docker-compose.yml` - Service configuration
