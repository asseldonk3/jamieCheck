"""
Configuration settings for A/B test analysis
"""
import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent

# Input/Output directories
INPUT_FILE = BASE_DIR.parent / "input" / "groeperen urls aug (1).xlsx"
SCREENSHOTS_DIR = BASE_DIR / "screenshots"
RESULTS_DIR = BASE_DIR / "results"
LOGS_DIR = BASE_DIR / "logs"

# A/B Test Parameters
VARIANT_A_PARAM = "5"  # Just the value, not the full parameter string
VARIANT_B_PARAM = "6"  # Just the value, not the full parameter string

# Selenium Settings
SELENIUM_TIMEOUT = 30
SELENIUM_WAIT_TIME = 3  # Time to wait after page load
WINDOW_WIDTH = 1920
WINDOW_HEIGHT = 1080

# OpenAI Settings
OPENAI_MODEL = "gpt-5-mini"  # Using GPT-5-mini for duplicate detection analysis
MAX_RETRIES = 3
RETRY_DELAY = 2

# Report Settings
REPORT_FILENAME = "ab_test_report"
PDF_PAGE_SIZE = "A4"

# Analysis Settings
SCORING_SCALE = 10  # 1-10 scale for relevance scoring
BATCH_SIZE = 10  # Process URLs in batches to avoid memory issues

# Screenshot Settings
SCREENSHOT_FORMAT = "png"
SCREENSHOT_QUALITY = 85  # For JPEG, not used for PNG