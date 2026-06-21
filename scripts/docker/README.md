# Docker Scripts

Automated setup and troubleshooting scripts for Docker deployment.

## Setup Scripts

### One-Command Setup (Recommended)

**Windows PowerShell:**
```powershell
.\setup-docker.ps1
```

**Windows Command Prompt:**
```cmd
setup-docker.bat
```

**Linux/Mac:**
```bash
chmod +x setup-docker.sh
./setup-docker.sh
```

**What it does:**
- ✅ Starts all Docker containers (Ollama, FastAPI backend, React frontend)
- ✅ Pulls required AI models (gemma-2-9b, nomic-embed-text)
- ✅ Creates persistent volumes for database and persona summaries
- ✅ Validates health of all services
- ✅ Runs post-startup verification (`verify_startup.py`)

## Post-Startup Verification (Mandatory)

**Run after every Docker rebuild.** This is the primary validation tool.

```bash
# Full verification (subsystem checks + live MCP test queries)
python scripts/docker/verify_startup.py

# Quick mode (subsystem checks only, no LLM queries)
python scripts/docker/verify_startup.py --skip-queries

# Custom timeout for slow starts
python scripts/docker/verify_startup.py --timeout 120
```

**What it checks:**
1. `/ready` endpoint returns 200 (database + Ollama healthy)
2. Brave MCP status matches `.env.docker` config (`BRAVE_API_KEY` set → must be `enabled`)
3. Persona list loads successfully
4. LLM greet returns a valid response
5. Brave search query returns a valid response (if enabled)

**Exit codes:** `0` = all checks passed, `1` = one or more checks failed.

## Legacy Validation Scripts

Basic Docker infrastructure tests (containers, ports, files). For MCP-level verification, use `verify_startup.py` instead.

**Windows:**
```powershell
.\test_docker_setup.ps1
```

**Linux/Mac:**
```bash
chmod +x test_docker_setup.sh
./test_docker_setup.sh
```

**Checks:**
- Container status (ai-companion-brain, ai-companion-api, ai-companion-web)
- Port accessibility (8000, 3000, 11434)
- Model availability (gemma-2-9b, nomic-embed-text)
- Database connectivity

## Troubleshooting Scripts

### Network Issues

**Symptoms:**
- "Network not found" errors
- Containers fail to start
- Cannot connect to services

**Fix (PowerShell):**
```powershell
# Quick fix (recommended)
.\fix-docker-network.ps1

# Full rebuild (nuclear option)
.\fix-docker-network.ps1 -Nuclear

# Check status only
.\fix-docker-network.ps1 -Verify
```

**Fix (Command Prompt):**
```cmd
.\fix-docker-network.bat
```

**What it does:**
- Stops all containers gracefully
- Removes orphaned networks
- Recreates Docker Compose stack
- Validates connectivity

## Common Issues

**Permission Denied:**
- Windows: Run as Administrator
- Linux/Mac: Use `sudo` or add user to docker group

**Port Already in Use:**
- Check for conflicting services on ports 3000, 8000, 11434
- Stop conflicting services or modify `.env.docker`

**Model Download Fails:**
- Verify internet connectivity
- Check Ollama container logs: `docker logs ai-companion-brain`
- Manually pull models: `docker exec ai-companion-brain ollama pull <model-name>`

## Related Documentation

- [../../docs/setup/DOCKER_QUICKSTART.md](../../docs/setup/DOCKER_QUICKSTART.md) - Complete Docker guide
- [../../CLAUDE.md](../../CLAUDE.md) - Development commands
- [../../.env.docker](../../.env.docker) - Configuration template
