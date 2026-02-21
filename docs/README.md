# Documentation Index

Organized documentation for MCP Coordinator development and deployment.

## Directory Structure

```
docs/
├── setup/          Setup and deployment guides
├── development/    Development guides and MCP integration
└── architecture/   Architecture decision records and system design
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
- Per-persona MCP access (Celestial Order)
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

# Primary: set mcp_access field on the persona JSON
# { "mcp_access": ["brave_search", "mongodb"] }
```

### [development/TESTING_GUIDE.md](development/TESTING_GUIDE.md)

**Testing setup and best practices**

**Test organization:**
- `tests/backend/` - Backend unit tests (~8 files)
- `tests/integration/` - End-to-end tests (~13 files)
- `tests/exploration/` - Archived exploratory scripts

**Running tests:**
```bash
# React tests
cd react-ui && npm test

# Python tests
pytest tests/backend/ -v
pytest tests/integration/ -v

# RAGAS evaluation (persona quality)
pytest tests/evaluation/test_persona_quality.py -v
pytest tests/evaluation/test_persona_quality.py --persona=eeva -v
```

### [development/DESIGN_SYSTEM.md](development/DESIGN_SYSTEM.md)

**Visual design language and UI component guidelines**

**Contents:**
- Typography: Outfit (display), Manrope (body), Space Mono (mono)
- Celestial Order colors: Wanderer, Sage, Warden, Archon palettes
- CSS variables and Tailwind configuration
- Card effects: holographic shimmer, rarity glows
- Glassmorphism recipe and usage rules
- WCAG AA contrast requirements and accessibility rules

### [development/PERSONA_SCHEMA.md](development/PERSONA_SCHEMA.md)

**Complete field reference for persona JSON definitions**

**Contents:**
- Complete field reference for `personas/*.json` with types, valid values, and examples
- Core fields (key, display_name, rarity, celestial_order, mcp_access)
- NEPHILIM extension fields (nephilim_lore, unlockable_lore, title, archetype)
- Voice and behavior configuration
- Validation rules and common mistakes

### [development/API_REFERENCE.md](development/API_REFERENCE.md)

**Backend REST API documentation**

**Contents:**
- All backend endpoints grouped by route file with request/response schemas
- Route files: chat.py, sessions.py, personas.py, nephilim.py
- Authentication and error handling patterns
- WebSocket and streaming endpoints

## Architecture

### [architecture/SQLITE_ARCHITECTURE.md](architecture/SQLITE_ARCHITECTURE.md)

**SQLite persistence layer design and implementation**

**Contents:**
- SQLite persistence layer: ADR, thread-safety pattern, schema, migrations
- Repository pattern with `_lock` thread-safety
- Schema: core tables, NEPHILIM progression tables
- Migration approach and adding new tables

### [architecture/WALLET_METADATA.md](architecture/WALLET_METADATA.md)

**Wallet metadata & AI context layer**

**Contents:**
- What data the AI companion can see per-message (wallet inventory, balances, trade history, lock state)
- Hard guardrails: 3-wallet limit, secret key ceremony, mnemonic wipe
- SQLite tables: wallet_registry, wallet_activity_summary, wallet_balance_cache, wallet_trades_local
- 4-step wallet creation flow with BIP39 mnemonic
- Dual-write trade pattern (MongoDB + SQLite fallback)
- Multi-companion access design

### [architecture/CELESTIAL_ORDER.md](architecture/CELESTIAL_ORDER.md)

**Four-tier Celestial Order system design**

**Contents:**
- Four-tier Celestial Order system: MCP access control, frontend theming, adding new tiers
- Tier definitions: Wanderer, Sage, Warden, Archon
- Per-persona `mcp_access` field and legacy env var fallback
- Frontend theming and color palette per tier

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
- Archive obsolete docs to `archive/` subdirectories
- Keep guides under 500 lines (split if larger)
- Use relative links for portability

## Need Help?

- **Setup issues**: See [setup/DOCKER_QUICKSTART.md](setup/DOCKER_QUICKSTART.md) troubleshooting section
- **MCP integration**: See [development/ADDING_MCP_SERVERS.md](development/ADDING_MCP_SERVERS.md)
- **Testing**: See [development/TESTING_GUIDE.md](development/TESTING_GUIDE.md)
- **Codebase questions**: See [../CLAUDE.md](../CLAUDE.md) project overview
