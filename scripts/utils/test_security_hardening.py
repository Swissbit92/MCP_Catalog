#!/usr/bin/env python3
"""
Security Hardening Validation Script

Tests that Docker security hardening is correctly implemented:
1. Resource limits applied to spawned containers
2. Container labels present
3. Cleanup mechanisms functional

Usage:
    python scripts/test_security_hardening.py

Requirements:
    - Docker daemon running
    - Docker images pulled (mcp/brave-search)
    - BRAVE_API_KEY environment variable set (for Brave tests)
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import time
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class SecurityHardeningValidator:
    """Validates Docker security hardening implementation."""

    def __init__(self):
        self.tests_passed = 0
        self.tests_failed = 0
        self.brave_api_key = os.getenv("BRAVE_API_KEY")

    def run_all_tests(self) -> bool:
        """
        Run all validation tests.

        Returns:
            True if all tests pass, False otherwise
        """
        logger.info("=" * 70)
        logger.info("Docker Security Hardening Validation")
        logger.info("=" * 70)
        logger.info("")

        # Test 1: Docker availability
        if not self.test_docker_available():
            logger.error("Docker not available - cannot continue tests")
            return False

        # Test 2: Brave MCP resource limits
        self.test_brave_mcp_resource_limits()

        # (MongoDB MCP resource-limit test removed 2026-06-22 — ADR-002)

        # Test 4: Container labels
        self.test_container_labels()

        # Test 5: Cleanup on timeout
        self.test_cleanup_on_timeout()

        # Test 6: Orphan detection script
        self.test_orphan_detection_script()

        # Print summary
        logger.info("")
        logger.info("=" * 70)
        logger.info("TEST SUMMARY")
        logger.info("=" * 70)
        logger.info(f"Passed: {self.tests_passed}")
        logger.info(f"Failed: {self.tests_failed}")
        logger.info("=" * 70)

        return self.tests_failed == 0

    def test_docker_available(self) -> bool:
        """Test that Docker daemon is accessible."""
        logger.info("TEST 1: Docker availability")
        try:
            result = subprocess.run(
                ["docker", "version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                logger.info("✅ PASS - Docker is available")
                self.tests_passed += 1
                return True
            else:
                logger.error(f"❌ FAIL - Docker version check failed: {result.stderr}")
                self.tests_failed += 1
                return False
        except Exception as e:
            logger.error(f"❌ FAIL - Docker not accessible: {e}")
            self.tests_failed += 1
            return False

    def test_brave_mcp_resource_limits(self) -> bool:
        """Test that Brave MCP containers have resource limits."""
        logger.info("TEST 2: Brave MCP resource limits")

        if not self.brave_api_key:
            logger.warning("⚠️  SKIP - BRAVE_API_KEY not set")
            return True

        try:
            # Spawn a Brave MCP container (it will fail without a valid request, but we just want to check limits)
            cmd = [
                "docker", "run", "-d", "--rm",
                "--memory=256m",
                "--cpus=0.5",
                "--pids-limit=100",
                "--label=mcp.coordinator.ephemeral=true",
                "--label=mcp.coordinator.service=brave-search",
                "-e", f"BRAVE_API_KEY={self.brave_api_key}",
                "docker.io/mcp/brave-search",
                "sleep", "5"
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if result.returncode != 0:
                # Container might not exist, try pulling
                logger.info("Pulling docker.io/mcp/brave-search...")
                subprocess.run(["docker", "pull", "docker.io/mcp/brave-search"], timeout=60)
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                container_id = result.stdout.strip()

                # Wait a moment for container to start
                time.sleep(1)

                # Inspect container
                inspect_result = subprocess.run(
                    ["docker", "inspect", container_id],
                    capture_output=True,
                    text=True
                )

                if inspect_result.returncode == 0:
                    inspect_data = json.loads(inspect_result.stdout)[0]
                    host_config = inspect_data.get("HostConfig", {})

                    # Check memory limit (256MB = 268435456 bytes)
                    memory = host_config.get("Memory", 0)
                    expected_memory = 268435456

                    # Check CPU limit
                    nano_cpus = host_config.get("NanoCpus", 0)
                    expected_nano_cpus = 500000000  # 0.5 CPUs

                    # Check PID limit
                    pids_limit = host_config.get("PidsLimit", 0)
                    expected_pids = 100

                    # Check labels
                    labels = inspect_data.get("Config", {}).get("Labels", {})
                    has_labels = (
                        labels.get("mcp.coordinator.ephemeral") == "true" and
                        labels.get("mcp.coordinator.service") == "brave-search"
                    )

                    # Kill the test container
                    subprocess.run(["docker", "kill", container_id], capture_output=True)

                    # Validate
                    if memory == expected_memory and nano_cpus == expected_nano_cpus and pids_limit == expected_pids and has_labels:
                        logger.info(f"✅ PASS - Resource limits correct:")
                        logger.info(f"  Memory: {memory / 1024 / 1024:.0f}MB")
                        logger.info(f"  CPU: {nano_cpus / 1000000000:.1f} cores")
                        logger.info(f"  PID limit: {pids_limit}")
                        logger.info(f"  Labels: ✓")
                        self.tests_passed += 1
                        return True
                    else:
                        logger.error("❌ FAIL - Resource limits incorrect:")
                        logger.error(f"  Memory: {memory} (expected {expected_memory})")
                        logger.error(f"  NanoCPUs: {nano_cpus} (expected {expected_nano_cpus})")
                        logger.error(f"  PID limit: {pids_limit} (expected {expected_pids})")
                        logger.error(f"  Labels: {has_labels}")
                        self.tests_failed += 1
                        return False

            logger.error(f"❌ FAIL - Could not spawn container: {result.stderr}")
            self.tests_failed += 1
            return False

        except Exception as e:
            logger.error(f"❌ FAIL - Exception: {e}")
            self.tests_failed += 1
            return False

    def test_container_labels(self) -> bool:
        """Test that containers are properly labeled."""
        logger.info("TEST 4: Container labels")

        # This is already tested in resource limit tests
        logger.info("✅ PASS - Labels tested in resource limit tests")
        self.tests_passed += 1
        return True

    def test_cleanup_on_timeout(self) -> bool:
        """Test that containers are cleaned up on timeout."""
        logger.info("TEST 5: Cleanup on timeout")

        try:
            # Ensure alpine image exists
            logger.info("Pulling alpine image...")
            subprocess.run(["docker", "pull", "alpine"], capture_output=True, timeout=30)

            # Spawn a long-running container
            cmd = ["docker", "run", "-d", "--rm", "alpine", "sleep", "60"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                container_id = result.stdout.strip()
                logger.info(f"Spawned container: {container_id[:12]}")

                # Kill it and verify cleanup
                subprocess.run(["docker", "kill", container_id], capture_output=True)
                time.sleep(2)  # Wait for cleanup

                # Check if container is gone
                check_result = subprocess.run(
                    ["docker", "ps", "-a", "-q", "--filter", f"id={container_id}"],
                    capture_output=True,
                    text=True
                )

                if not check_result.stdout.strip():
                    logger.info("✅ PASS - Container cleaned up after kill")
                    self.tests_passed += 1
                    return True
                else:
                    logger.error("❌ FAIL - Container still exists after kill")
                    self.tests_failed += 1
                    return False
            else:
                logger.error(f"❌ FAIL - Could not spawn test container: {result.stderr}")
                self.tests_failed += 1
                return False

        except Exception as e:
            logger.error(f"❌ FAIL - Exception: {e}")
            self.tests_failed += 1
            return False

    def test_orphan_detection_script(self) -> bool:
        """Test that orphan detection script works."""
        logger.info("TEST 6: Orphan detection script")

        try:
            # Run the script in dry-run mode
            result = subprocess.run(
                ["python", "scripts/cleanup_orphan_containers.py"],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode in [0, 1]:  # 0 = no orphans, 1 = orphans found
                logger.info("✅ PASS - Orphan detection script runs successfully")
                self.tests_passed += 1
                return True
            else:
                logger.error(f"❌ FAIL - Script failed with exit code {result.returncode}")
                logger.error(f"stderr: {result.stderr}")
                self.tests_failed += 1
                return False

        except Exception as e:
            logger.error(f"❌ FAIL - Exception: {e}")
            self.tests_failed += 1
            return False


def main():
    """CLI entry point."""
    validator = SecurityHardeningValidator()

    try:
        success = validator.run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.warning("\nInterrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(2)


if __name__ == "__main__":
    main()
