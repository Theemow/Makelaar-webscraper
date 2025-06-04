"""
Selenium Helper module for configuring WebDriver properly in Docker environment.

This module provides utility functions for creating a properly configured WebDriver
instance that works both in development and Docker environments.
"""

import os
import logging
from typing import Optional

logger = logging.getLogger("selenium_helper")


def create_chrome_driver(headless: bool = True) -> Optional["webdriver.Chrome"]:
    """
    Create a Chrome WebDriver instance configured for either local or Docker environment.

    Args:
        headless: Whether to run Chrome in headless mode

    Returns:
        A configured Chrome WebDriver instance, or None if setup fails
    """
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service

        # Try to use webdriver_manager first (development environment)
        try:
            from webdriver_manager.chrome import ChromeDriverManager

            service = Service(ChromeDriverManager().install())
        except Exception as e:
            logger.info(f"Could not use webdriver_manager: {e}")
            logger.info("Falling back to system Chrome in Docker environment")
            service = Service("/usr/bin/chromedriver")

        # Configure Chrome options for headless operation in Docker
        options = Options()

        if headless:
            options.add_argument("--headless")

        # Required options for running in Docker
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-extensions")

        # For Docker environment
        if os.environ.get("DOCKER_ENVIRONMENT"):
            options.binary_location = "/usr/bin/google-chrome"

        # Create and return the driver
        driver = webdriver.Chrome(service=service, options=options)
        return driver

    except Exception as e:
        logger.error(f"Failed to create Chrome WebDriver: {e}")
        return None


def quit_driver(driver: Optional["webdriver.Chrome"]) -> None:
    """
    Safely quit the WebDriver if it exists.

    Args:
        driver: The WebDriver instance to quit
    """
    if driver is not None:
        try:
            driver.quit()
        except Exception as e:
            logger.error(f"Error closing Chrome WebDriver: {e}")
