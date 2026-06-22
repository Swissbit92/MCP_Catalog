# Scripts Directory

Organized collection of utility scripts for MCP Coordinator development and deployment.

## Directory Structure

```
scripts/
├── docker/          Docker deployment and troubleshooting scripts
├── setup/           Local development setup scripts
└── utils/           Python utility scripts
```

## Quick Reference

### Docker Scripts (`docker/`)
- **Setup**: `setup-docker.sh` (macOS/Linux, primary) — `setup-docker.ps1` / `.bat` (Windows reference)
- **Networking**: `fix-docker-network.ps1` (Windows-only reference; macOS/Linux use the manual `docker-compose` steps in [docker/README.md](docker/README.md))
- **Validation**: `test_docker_setup.sh` (macOS/Linux, primary) — `test_docker_setup.ps1` (Windows reference)

See [docker/README.md](docker/README.md) for usage examples.

### Setup Scripts (`setup/`)
- **Automated**: `setup.sh` (macOS/Linux) — Install Python + React dependencies

See [setup/README.md](setup/README.md) for prerequisites.

### Python Utilities (`utils/`)
- **Unified Launcher**: `run_react.py` - Start backend + frontend together
- **QA Validation**: `validate_golden_qa.py` - Validate persona responses
- **Docker Cleanup**: `cleanup_orphan_containers.py` - Remove orphaned containers
- **Security**: `test_security_hardening.py` - Validate security configurations

See [utils/README.md](utils/README.md) for import examples.

## Related Documentation

- [docs/setup/DOCKER_QUICKSTART.md](../docs/setup/DOCKER_QUICKSTART.md) - Docker deployment guide
- [CLAUDE.md](../CLAUDE.md) - Development commands reference
- [README.md](../README.md) - Main project documentation
