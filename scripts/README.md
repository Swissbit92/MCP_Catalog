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
- **Setup**: `setup-docker.sh`, `setup-docker.bat`, `setup-docker.ps1`
- **Networking**: `fix-docker-network.ps1`, `fix-docker-network.bat`
- **Validation**: `test_docker_setup.sh`, `test_docker_setup.ps1`

See [docker/README.md](docker/README.md) for usage examples.

### Setup Scripts (`setup/`)
- **Automated**: `setup.sh`, `setup.bat` - Install Python + React dependencies
- **Backend**: `start_backend.bat` - Windows backend launcher

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
