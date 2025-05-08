"""
Logging service for the HuurhuisWebscraper application.

This module provides a centralized logging service used throughout the application
to ensure consistent logging to both console and file.
"""

import logging
import os
import threading
from datetime import datetime
from typing import List, Optional


class LogService:
    """
    Centralized logging service for the HuurhuisWebscraper application.

    This class manages logging to both console and file with appropriate formatting.
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

        # Create logs directory if it doesn't exist
        log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # Generate log filename with current timestamp
        current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = os.path.join(log_dir, f"huurhuis_webscraper_{current_time}.log")

        # Set up root logger
        self.root_logger = logging.getLogger()
        self.root_logger.setLevel(logging.INFO)

        # Remove existing handlers to avoid duplicate logs
        for handler in self.root_logger.handlers[:]:
            self.root_logger.removeHandler(handler)

        # Create console handler with thread information
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_format = logging.Formatter(
            "%(asctime)s - [%(threadName)s] - %(name)s - %(levelname)s - %(message)s"
        )
        console_handler.setFormatter(console_format)

        # Create file handler for summary log with thread information
        file_handler = logging.FileHandler(log_filename)
        file_handler.setLevel(logging.INFO)
        file_format = logging.Formatter(
            "%(asctime)s - [%(threadName)s] - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(file_format)

        # Add handlers to the root logger
        self.root_logger.addHandler(console_handler)
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

    def log_broker_processing(
        self, broker_name: str, new_count: int, removed_count: int
    ) -> None:
        """
        Log summary of a broker agency processing.

        Args:
            broker_name: Name of the broker agency
            new_count: Number of new properties found for this broker
            removed_count: Number of removed properties for this broker
        """
        self.root_logger.info(
            f"Broker: {broker_name} | New properties: {new_count} | Removed properties: {removed_count}"
        )


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
