#!/usr/bin/env python3
"""
Orphan MCP Container Cleanup Script

Detects and removes orphaned MCP containers that failed to cleanup properly.
These can occur when:
- Parent process crashes before container cleanup
- Kill signals don't propagate properly
- Unexpected errors during container lifecycle

Usage:
    python scripts/cleanup_orphan_containers.py          # Dry run (list only)
    python scripts/cleanup_orphan_containers.py --kill   # Kill orphans
    python scripts/cleanup_orphan_containers.py --force  # Force kill all MCP containers

Should be run periodically as a cron job or monitoring task.
"""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class OrphanContainerCleaner:
    """Detects and cleans up orphaned MCP containers."""

    # Labels applied by MCP clients
    MCP_LABEL = "mcp.coordinator.service"
    EPHEMERAL_LABEL = "mcp.coordinator.ephemeral"

    # Maximum age for ephemeral containers (should die in <30s)
    EPHEMERAL_MAX_AGE_SECONDS = 60

    # Maximum age for long-running containers (should restart if parent dies)
    LONG_RUNNING_MAX_AGE_HOURS = 24

    def __init__(self, dry_run: bool = True):
        """
        Initialize cleaner.

        Args:
            dry_run: If True, only report orphans without killing
        """
        self.dry_run = dry_run

    def get_mcp_containers(self) -> List[Dict[str, Any]]:
        """
        Get all MCP containers (running or stopped).

        Returns:
            List of container info dicts
        """
        try:
            # Get containers with MCP labels
            result = subprocess.run(
                [
                    "docker", "ps", "-a",
                    "--filter", f"label={self.MCP_LABEL}",
                    "--format", "{{json .}}"
                ],
                capture_output=True,
                text=True,
                check=True
            )

            containers = []
            for line in result.stdout.strip().split("\n"):
                if line:
                    containers.append(json.loads(line))

            return containers

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to list containers: {e}")
            return []
        except FileNotFoundError:
            logger.error("Docker command not found - is Docker installed?")
            return []

    def get_container_details(self, container_id: str) -> Dict[str, Any]:
        """
        Get detailed container information.

        Args:
            container_id: Container ID or name

        Returns:
            Container inspect data
        """
        try:
            result = subprocess.run(
                ["docker", "inspect", container_id],
                capture_output=True,
                text=True,
                check=True
            )
            data = json.loads(result.stdout)
            return data[0] if data else {}

        except Exception as e:
            logger.warning(f"Failed to inspect {container_id}: {e}")
            return {}

    def is_orphan(self, container: Dict[str, Any]) -> tuple[bool, str]:
        """
        Determine if a container is an orphan.

        Args:
            container: Container info from docker ps

        Returns:
            (is_orphan, reason)
        """
        container_id = container.get("ID", "unknown")
        details = self.get_container_details(container_id)

        if not details:
            return False, "Could not inspect container"

        # Check labels
        labels = details.get("Config", {}).get("Labels", {})
        is_ephemeral = labels.get(self.EPHEMERAL_LABEL) == "true"
        service = labels.get(self.MCP_LABEL, "unknown")

        # Check state
        state = details.get("State", {})
        status = state.get("Status", "unknown")
        started_at = state.get("StartedAt", "")

        # Calculate age
        try:
            start_time = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
            age = datetime.now(start_time.tzinfo) - start_time
        except Exception:
            return False, "Could not parse start time"

        # Ephemeral containers should die quickly
        if is_ephemeral:
            if status == "running" and age.total_seconds() > self.EPHEMERAL_MAX_AGE_SECONDS:
                return True, f"Ephemeral {service} container running for {age.total_seconds():.0f}s (max {self.EPHEMERAL_MAX_AGE_SECONDS}s)"

            if status == "exited":
                # Exited ephemeral containers should auto-remove (--rm flag)
                # If they still exist, something went wrong
                return True, f"Ephemeral {service} container failed to auto-remove"

        # Long-running containers shouldn't be running if parent is dead
        # This is harder to detect, so we use age as a heuristic
        else:
            if status == "running" and age.total_seconds() > self.LONG_RUNNING_MAX_AGE_HOURS * 3600:
                return True, f"Long-running {service} container active for {age.total_seconds() / 3600:.1f}h"

            if status == "exited":
                return True, f"Long-running {service} container exited (should restart)"

        return False, ""

    def kill_container(self, container_id: str, force: bool = False) -> bool:
        """
        Kill a container.

        Args:
            container_id: Container ID
            force: Use force kill (SIGKILL) instead of graceful (SIGTERM)

        Returns:
            True if successful
        """
        try:
            if force:
                subprocess.run(
                    ["docker", "kill", container_id],
                    check=True,
                    capture_output=True
                )
                logger.info(f"Force killed container {container_id[:12]}")
            else:
                subprocess.run(
                    ["docker", "stop", "-t", "5", container_id],
                    check=True,
                    capture_output=True
                )
                logger.info(f"Stopped container {container_id[:12]}")

            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to kill {container_id[:12]}: {e}")
            return False

    def cleanup_orphans(self, force_all: bool = False) -> Dict[str, int]:
        """
        Scan and cleanup orphaned containers.

        Args:
            force_all: If True, kill ALL MCP containers (emergency cleanup)

        Returns:
            Stats dict with counts
        """
        stats = {
            "total": 0,
            "orphans": 0,
            "killed": 0,
            "failed": 0
        }

        containers = self.get_mcp_containers()
        stats["total"] = len(containers)

        if not containers:
            logger.info("No MCP containers found")
            return stats

        logger.info(f"Found {len(containers)} MCP containers")

        for container in containers:
            container_id = container.get("ID", "unknown")
            names = container.get("Names", "unknown")
            status = container.get("Status", "unknown")

            # Check if orphan (or force kill all)
            if force_all:
                is_orphan = True
                reason = "Force cleanup requested"
            else:
                is_orphan, reason = self.is_orphan(container)

            if is_orphan:
                stats["orphans"] += 1
                logger.warning(f"ORPHAN: {container_id[:12]} ({names}) - {reason}")

                if not self.dry_run:
                    # Kill the orphan
                    if self.kill_container(container_id, force=force_all):
                        stats["killed"] += 1
                    else:
                        stats["failed"] += 1
            else:
                logger.debug(f"OK: {container_id[:12]} ({names}) - {status}")

        return stats

    def run(self, force_all: bool = False) -> int:
        """
        Run cleanup and return exit code.

        Args:
            force_all: Force kill all MCP containers

        Returns:
            Exit code (0 = success, 1 = orphans found, 2 = error)
        """
        try:
            if self.dry_run:
                logger.info("DRY RUN MODE - will not kill containers")
            elif force_all:
                logger.warning("FORCE MODE - will kill ALL MCP containers")
            else:
                logger.info("CLEANUP MODE - will kill orphaned containers")

            stats = self.cleanup_orphans(force_all=force_all)

            # Print summary
            logger.info("")
            logger.info("=" * 60)
            logger.info("CLEANUP SUMMARY")
            logger.info("=" * 60)
            logger.info(f"Total MCP containers: {stats['total']}")
            logger.info(f"Orphans detected:     {stats['orphans']}")
            if not self.dry_run:
                logger.info(f"Successfully killed:  {stats['killed']}")
                logger.info(f"Failed to kill:       {stats['failed']}")
            logger.info("=" * 60)

            # Return appropriate exit code
            if stats["failed"] > 0:
                return 2  # Error
            elif stats["orphans"] > 0 and self.dry_run:
                return 1  # Orphans found
            else:
                return 0  # Success

        except KeyboardInterrupt:
            logger.warning("Interrupted by user")
            return 130
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            return 2


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Cleanup orphaned MCP containers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run (list orphans only)
  python scripts/cleanup_orphan_containers.py

  # Kill orphaned containers
  python scripts/cleanup_orphan_containers.py --kill

  # Emergency: Force kill ALL MCP containers
  python scripts/cleanup_orphan_containers.py --force

Exit Codes:
  0 = Success (no orphans or all cleaned)
  1 = Orphans detected (dry run)
  2 = Error during cleanup
        """
    )

    parser.add_argument(
        "--kill",
        action="store_true",
        help="Kill orphaned containers (default: dry run)"
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Force kill ALL MCP containers (emergency cleanup)"
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging"
    )

    args = parser.parse_args()

    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Create cleaner
    dry_run = not (args.kill or args.force)
    cleaner = OrphanContainerCleaner(dry_run=dry_run)

    # Run cleanup
    exit_code = cleaner.run(force_all=args.force)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
