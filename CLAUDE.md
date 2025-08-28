# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## CC1 Documentation System

This project uses the CC1 documentation system for maintaining institutional knowledge across Claude sessions. CC1 files are located in the `cc1/` directory:

- **cc1/TASKS.md** - Active task tracking and sprint management
- **cc1/LEARNINGS.md** - Captured mistakes, solutions, and patterns
- **cc1/PROJECT_INDEX.md** - Technical specs and project structure
- **cc1/BACKLOG.md** - Future features and deferred work

When working on this project:
1. Check cc1/TASKS.md for current priorities
2. Reference cc1/LEARNINGS.md for known issues and solutions
3. Update CC1 docs when discovering important patterns
4. Use `/cc1-update` command to review and update documentation

_CC1 System initialized: 2025-08-27_

## Project Overview

This repository contains two interconnected e-commerce analysis systems:

1. **Main Product Analysis Tool**: Fetches product data from the Beslist.nl affiliate network API, captures screenshots, and uses GPT-5-mini vision to analyze product features and generate PDF reports

2. **A/B Testing System** (in `grouptest/`): Analyzes product page variants to determine which performs better using visual AI analysis

## Core Architecture

The application consists of three main components:

1. **API Client (api_client.py)**: Interfaces with Beslist.nl's product search and direct match APIs to fetch product listings and vendor URLs
2. **Product Analyzer (product_analyzer.py)**: Uses Selenium WebDriver to capture screenshots and GPT-5-mini to analyze product page features like sale indicators, reviews, and shipping information
3. **Main Orchestrator (analyze_and_report.py)**: Coordinates the data fetching and analysis pipeline, generating timestamped reports

## Commands

### Main Product Analysis Pipeline
```bash
# Basic usage - fetches products and generates analysis report
python analyze_and_report.py

# With custom parameters
python analyze_and_report.py --category "schoenen" --limit 20

# Skip data fetching and use existing data
python analyze_and_report.py --skip-fetch
```

### A/B Testing Analysis (grouptest/)
```bash
cd grouptest

# Run full A/B test analysis (200 URLs)
python run_ab_test.py

# Test mode with first 5 URLs
python run_ab_test.py --test

# Custom URL limit
python run_ab_test.py --limit 50

# Monitor progress during long runs
python monitor_progress.py
```

### Fetching Product Data Only
```bash
# Fetch product data without analysis
python api_client.py

# Fetch specific product by PIM ID
python api_client.py --pim-id "specific_id"

# Custom category and limit
python api_client.py --category "mode" --limit 100
```

### Installation and Dependencies
```bash
# Install required packages
pip install -r requirements.txt

# For A/B testing system
cd grouptest && pip install -r requirements.txt && cd ..

# Required environment variable (in .env file)
OPENAI_API_KEY=your_api_key_here

# Install Playwright browsers (for A/B testing)
playwright install chromium
```

### Development Commands
```bash
# Check code quality (if configured)
python -m flake8 *.py  # or ruff check
python -m mypy *.py    # type checking

# Run tests (if available)
python -m pytest tests/
```

## Data Flow

1. **Product Search**: Fetches popular products from Beslist.nl's product search API based on category
2. **Direct Match**: For each product, fetches vendor URLs (up to 3 lowest prices) using the direct match API
3. **Screenshot Capture**: Uses Selenium to capture screenshots of each product page
4. **AI Analysis**: Sends screenshots to GPT-5-mini for feature detection (sales, reviews, shipping info)
5. **Report Generation**: Creates PDF reports with analysis results and screenshots using ReportLab

## Key Configuration (config.py)

- `DEFAULT_CATEGORY`: Default product category for searches (currently "mode")
- `DEFAULT_LIMIT`: Number of products to fetch (default: 50)
- `DIRECT_MATCH_LIMIT`: Number of vendor URLs per product (default: 3)
- `DIRECT_MATCH_SORT`: Sort vendor results by price (ascending)

## Output Structure

### Main Analysis System
```
/data/                          # API data storage
  fetch_YYYYMMDD_HHMMSS/       # Timestamped fetch results
    product_search.json        # Raw product search results
    products_with_pim.json     # Products with PIM IDs
    final_result.json          # Processed results with vendor URLs
  latest_result.json           # Most recent fetch results

/analysis_results/              # Analysis outputs
  analysis_YYYYMMDD_HHMMSS/   # Timestamped analysis
    screenshots/               # Product page screenshots
    results/                   # Individual product analysis JSONs
    all_analysis_results.json  # Combined analysis results
    product_analysis_report_*.pdf  # Final PDF report
```

### A/B Testing System (grouptest/)
```
/grouptest/
  screenshots/              # A/B variant screenshots
    url_XXX_variant_A_*.png
    url_XXX_variant_B_*.png
  results/                 # Analysis results
    result_XXX.json       # Individual URL analysis
    all_results.json      # Combined results
    statistics.json       # Summary statistics
  logs/                   # Execution logs
    ab_test_*.log
  ab_test_report_*.pdf    # Final PDF report with winners
```

## API Endpoints Used

- **Product Search**: `https://productsearch.api.beslist.nl/productsearch`
- **Direct Match**: `https://productsearch.api.beslist.nl/directmatch`

Both endpoints require country parameter ("nl") and return JSON responses with product/vendor data.

## Important Implementation Details

- The system uses Selenium with Chrome WebDriver for screenshot capture
- Screenshots are analyzed using GPT-5-mini's vision capabilities with structured JSON responses
- PDF reports include both screenshots and analysis summaries in a tabular format
- The analyzer implements retry logic for web scraping stability
- All timestamps use format: YYYYMMDD_HHMMSS for consistent ordering

## AI Model Configuration

The system uses **GPT-5-mini** for all AI-powered analysis tasks:
- **Model Name**: `gpt-5-mini` 
- **Purpose**: Fast, cost-efficient vision and text analysis
- **Use Cases**:
  - Analyzing product page screenshots for features (sales, reviews, shipping)
  - Comparing A/B test variants to determine winners
  - Extracting structured data from visual content
- **Configuration**: Set in environment variable `OPENAI_API_KEY`

## Common Issues & Solutions

- **Chrome WebDriver Issues**: Run `webdriver-manager update` to fix driver version mismatches
- **Screenshot Timeouts**: Increase `PAGE_LOAD_TIMEOUT` in config.py
- **API Rate Limits**: Add delays between requests or reduce batch sizes
- **Memory Issues with Large Batches**: Process in smaller chunks using `--limit` parameter