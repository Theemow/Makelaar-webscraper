#!/usr/bin/env python3
"""
Test script to verify Docker logging functionality.

This script can be used to test whether logs are properly captured
by Docker and visible in Portainer.
"""

import os
import sys
import time
from datetime import datetime

# Add current directory to path to import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from log_service import LogService


def test_docker_logging():
    """Test Docker logging functionality."""

    # Initialize logging service
    log_service = LogService()
    logger = log_service.get_logger("test_docker_logging")

    # Test various log levels
    logger.info("=== Docker Logging Test Started ===")
    logger.info(f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Docker environment: {os.getenv('DOCKER_ENVIRONMENT', 'false')}")
    logger.info(f"Python unbuffered: {os.getenv('PYTHONUNBUFFERED', 'not set')}")

    # Test with different message types
    logger.info("This is an INFO message")
    logger.warning("This is a WARNING message")
    logger.error("This is an ERROR message (test only)")

    # Test with some delays to see real-time logging
    for i in range(5):
        logger.info(
            f"Test message {i+1}/5 - timestamp: {datetime.now().strftime('%H:%M:%S')}"
        )
        time.sleep(2)

    # Test print statements as well
    print("Direct print statement - should also appear in Docker logs")
    sys.stdout.flush()

    # Test stderr
    print("Error message via stderr", file=sys.stderr)
    sys.stderr.flush()

    logger.info("=== Docker Logging Test Completed ===")


if __name__ == "__main__":
    test_docker_logging()
