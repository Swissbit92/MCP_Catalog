# Documentation Index

Organized documentation for MCP Coordinator development and deployment.

## Directory Structure

```
docs/
├── setup/          Setup and deployment guides
└── development/    Development guides and MCP integration
```

## Setup & Deployment

### [setup/DOCKER_QUICKSTART.md](setup/DOCKER_QUICKSTART.md)

**Complete Docker deployment guide** (Recommended setup method)

**Contents:**
- One-command setup for Windows/Linux/Mac
- Manual deployment steps
- Environment configuration
- Troubleshooting guide
- Network debugging
- Container health checks

**Quick start:**
```bash
# Windows PowerShell
.\scripts\docker\setup-docker.ps1

# Linux/Mac
./scripts/docker/setup-docker.sh
```

## Development

### [development/ADDING_MCP_SERVERS.md](development/ADDING_MCP_SERVERS.md)

**Guide for integrating new MCP (Model Context Protocol) servers**

**Topics covered:**
- MCP server architecture (ephemeral vs long-running)
- Docker container configuration
- Tool definition and schema
- Rarity-based feature gating
- Intent classification integration
- Citation and response synthesis

**Current MCP servers:**
- Brave Search (ephemeral, 2-3s lifecycle)
- MongoDB (long-running, stateful)

**Example integration:**
```python
# Add to tool_definitions.py
BRAVE_SEARCH_TOOL = {
    "name": "brave_web_search",
    "description": "Search the web using Brave Search API",
    "input_schema": {...}
}

# Enable for rarities in .env
BRAVE_ENABLED_RARITIES=rare,epic,legendary
```

### [development/TESTING_GUIDE.md](development/TESTING_GUIDE.md)

**Testing setup and best practices**

**Test organization:**
- `tests/backend/` - Backend unit tests (12 files)
- `tests/integration/` - End-to-end tests (23 files)
- `tests/exploration/` - Exploratory tests (10 files)

**Running tests:**
```bash
# React tests
cd react-ui && npm test

# Python tests (standalone scripts)
python tests/backend/coordinator/test_server.py
python tests/integration/test_brave_mcp_connectivity.py

# RAGAS evaluation (persona quality)
pytest tests/evaluation/test_persona_quality.py -v
pytest tests/evaluation/test_persona_quality.py --persona=eeva -v
```

## Root Documentation

Essential documentation files in project root:

| Document | Description |
|----------|-------------|
| **[../README.md](../README.md)** | Main project overview and quick start |
| **[../CLAUDE.md](../CLAUDE.md)** | AI coding guidelines and development commands |
| **[../CHANGELOG.md](../CHANGELOG.md)** | Version history and feature additions |

## Scripts

Development and deployment scripts:

```
../scripts/
├── docker/     Docker setup and troubleshooting (7 scripts)
├── setup/      Local development setup (3 scripts)
└── utils/      Python utilities (4 scripts)
```

See [../scripts/README.md](../scripts/README.md) for full reference.

## Documentation Standards

**Format:** GitHub-flavored Markdown with CommonMark spec

**Structure:**
- Clear section headers (## H2 for main sections)
- Code blocks with language hints (```bash, ```python)
- Usage examples before detailed explanations
- Related docs linked at bottom

**Maintenance:**
- Update on major feature changes
- Archive obsolete docs to git history
- Keep guides under 500 lines (split if larger)
- Use relative links for portability

## Need Help?

- **Setup issues**: See [setup/DOCKER_QUICKSTART.md](setup/DOCKER_QUICKSTART.md) troubleshooting section
- **MCP integration**: See [development/ADDING_MCP_SERVERS.md](development/ADDING_MCP_SERVERS.md)
- **Testing**: See [development/TESTING_GUIDE.md](development/TESTING_GUIDE.md)
- **Codebase questions**: See [../CLAUDE.md](../CLAUDE.md) project overview
