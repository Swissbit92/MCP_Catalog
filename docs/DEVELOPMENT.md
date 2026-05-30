---
title: Development Commands (nephilim)
status: active
created: 2026-04-19
last_reviewed_on: 2026-04-19
review_in: 6 months
applies_to: nephilim
---

# Development Commands

> Moved verbatim from CLAUDE.md 2026-04-19 as part of the /cms migration. Agents load this lazily when they need command details rather than on every session.

## Docker (Recommended)

```bash
# One-command setup
.\scripts\docker\setup-docker.ps1    # Windows PowerShell
./scripts/docker/setup-docker.sh     # Linux/Mac

# Manual start
docker-compose --env-file .env.docker up -d

# Pull models (required on first run)
docker exec -it ai-companion-brain ollama pull gemma2:9b-instruct-q5_K_M
docker exec -it ai-companion-brain ollama pull nomic-embed-text:latest

# Common operations
docker-compose logs -f backend       # View logs
docker-compose restart backend       # Restart
docker-compose down                  # Stop all

# Rebuild backend (ALWAYS verify after rebuild)
docker-compose --env-file .env.docker build --no-cache backend
docker-compose --env-file .env.docker up -d backend
python scripts/docker/verify_startup.py          # Mandatory post-rebuild check
python scripts/docker/verify_startup.py --skip-queries  # Quick mode (subsystems only)
```

**Access:** Frontend `http://localhost:3000` | Backend `http://localhost:8000` | API Docs `http://localhost:8000/docs`

> **⚠️ Note:** Docker serves legacy UI unless rebuilt. For Phase 7 NEPHILIM UI, use local development.

## Local Development (Phase 7 NEPHILIM UI)

```bash
# Setup
pip install -r requirements.txt
cd react-ui && npm install

# Run Phase 7 NEPHILIM UI (Terminal 1)
python -m uvicorn src.coordinator.server:app --reload --port 8000

# Run Phase 7 NEPHILIM UI (Terminal 2)
cd react-ui && PORT=3001 npx react-scripts start

# Access at http://localhost:3001

# Run Legacy UI (unified - starts both on port 3000)
python scripts/utils/run_react.py

# Build
cd react-ui && npm run build
```

**CORS Configuration:** `src/coordinator/server.py:41` allows `localhost:3000` and `localhost:3001`

## Testing

```bash
# React tests
cd react-ui && npm test
cd react-ui && npm test -- --testNamePattern="MessageBubble" --watchAll=false

# Playwright E2E tests
cd react-ui && npx playwright test                    # Run all E2E tests
cd react-ui && npx playwright test --headed           # Run with browser visible

# Python tests (run from project root)
pytest tests/backend/                    # Backend unit tests
pytest tests/integration/                # Integration tests
pytest tests/evaluation/ -v              # RAGAS persona quality
```

## Comprehensive Persona Test Suite (primary quality gate)

**Do NOT create new persona tests** — the suite covers all 8 personas across all MCPs and behavioral dimensions.

```bash
# Full run — all 8 personas, ~1045 tests (~60 min, requires backend on port 8000)
python tests/manual/comprehensive_persona_test.py

# Single persona (fast, ~10-15 min)
python tests/manual/comprehensive_persona_test.py --persona nephilim_eeva

# Quick sanity check — 30 tests per persona, no MCP bank (~8 min)
python tests/manual/comprehensive_persona_test.py --quick
```

Results saved to `tests/manual/results/`. Pass threshold: composite >= 0.60. Suite pass: >= 70%.

> **Scoring dimensions, test bank structure, and baseline results:** See [NEPHILIM_REFERENCE.md](NEPHILIM_REFERENCE.md).

## Ollama Setup

```bash
ollama serve                                               # Start service
ollama pull gemma2:9b-instruct-q5_K_M                     # Main model (best storytelling + safety balance)
ollama pull nomic-embed-text:latest                        # Embeddings (RAG memory)
# Optional: ollama pull nchapman/gemma-2-9b-it-abliterated:9b  # Alt model (PERSONA_MODEL_B)
```
