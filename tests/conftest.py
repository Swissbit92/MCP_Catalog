"""Shared pytest fixtures and configuration for MCP Coordinator tests."""
import sys
from pathlib import Path

# Add src to path for all tests
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

# This allows imports like: from coordinator.server import app
