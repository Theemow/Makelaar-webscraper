"""
Logging service for the HuurhuisWebscraper application.

This module provides a centralized logging service used throughout the application
to ensure consistent logging focused on stdout (standard Docker practice) with
optional file logging when not running in Docker.
"""

import logging
import os
import sys
import threading
from datetime import datetime
from typing import List, Optional


class LogService:
    """
    Centralized logging service for the HuurhuisWebscraper application.

    This class manages logging to stdout (Docker-friendly) with optional file logging
    when not running in Docker environment.
    """

    _instance = None
    _initialized = False

    def __new__(cls):
        """Singleton pattern to ensure only one logger instance exists."""
        if cls._instance is None:
            cls._instance = super(LogService, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the logging service if not already initialized."""
        if LogService._initialized:
            return

        # Set up root logger
        self.root_logger = logging.getLogger()
        self.root_logger.setLevel(logging.INFO)

        # Remove existing handlers to avoid duplicate logs
        for handler in self.root_logger.handlers[:]:
            self.root_logger.removeHandler(handler)

        # Check if running in Docker environment
        is_docker = os.environ.get("DOCKER_ENVIRONMENT", "false").lower() == "true"

        # Create console handler with thread information (Docker standard practice)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)

        # Force flush after each log message for immediate Docker output
        console_handler.stream = sys.stdout

        # Use a simpler format that's more Docker-friendly
        console_format = logging.Formatter(
            "%(asctime)s - [%(threadName)s] - %(name)s - %(levelname)s - %(message)s"
        )
        console_handler.setFormatter(
            console_format
        )  # Add console handler to the root logger (always needed)
        self.root_logger.addHandler(console_handler)

        # Force immediate flushing of all log messages in Docker
        if is_docker:
            # Override the emit method to force flush
            original_emit = console_handler.emit

            def flush_emit(record):
                original_emit(record)
                sys.stdout.flush()

            console_handler.emit = flush_emit

        # Add file logging only when not in Docker environment

        if not is_docker:
            # Create logs directory if it doesn't exist (only for non-Docker environments)
            log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)

            # Generate log filename with current timestamp
            current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_filename = os.path.join(
                log_dir, f"huurhuis_webscraper_{current_time}.log"
            )

            # Create file handler for summary log with thread information
            file_handler = logging.FileHandler(log_filename)
            file_handler.setLevel(logging.INFO)
            file_format = logging.Formatter(
                "%(asctime)s - [%(threadName)s] - %(levelname)s - %(message)s"
            )
            file_handler.setFormatter(file_format)

            # Add file handler only in non-Docker environments
            self.root_logger.addHandler(file_handler)

        # Set initialization flag
        LogService._initialized = True

        # Log start of application
        self.log_app_start()

    def get_logger(self, name: str) -> logging.Logger:
        """
        Get a named logger that will use the centralized configuration.

        Args:
            name: The name of the logger to get, typically the module name.

        Returns:
            A configured logger instance.
        """
        return logging.getLogger(name)

    def log_app_start(self) -> None:
        """Log the application start time."""
        self.root_logger.info("===== HuurhuisWebscraper Started =====")
        self.root_logger.info(
            f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

    def log_app_end(
        self, new_properties_count: int, removed_properties_count: int
    ) -> None:
        """
        Log the application end time and summary statistics.

        Args:
            new_properties_count: Number of new properties found
            removed_properties_count: Number of properties removed from the database
        """
        self.root_logger.info("===== HuurhuisWebscraper Completed =====")
        self.root_logger.info(
            f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        self.root_logger.info(f"New properties found: {new_properties_count}")
        self.root_logger.info(f"Properties removed: {removed_properties_count}")

    def log_email_sent(self, success: bool, recipients: List[str]) -> None:
        """
        Log whether the email notification was successfully sent.

        Args:
            success: Whether the email was successfully sent
            recipients: List of email recipients
        """
        if success:
            recipient_str = (
                ", ".join(recipients) if isinstance(recipients, list) else recipients
            )
            self.root_logger.info(
                f"Email notification successfully sent to: {recipient_str}"
            )
        else:
            self.root_logger.error("Failed to send email notification")


# Function to get the singleton instance
def get_logger(name: str) -> logging.Logger:
    """
    Get a named logger that uses the centralized configuration.

    Args:
        name: The name for the logger, typically the module name

    Returns:
        A configured logger instance
    """
    # Ensure LogService is initialized
    LogService()
    # Get a named logger
    return logging.getLogger(name)
