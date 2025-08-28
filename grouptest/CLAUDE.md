# CLAUDE.md - A/B Test Analysis System

## Project Overview

This is an A/B testing analysis tool that uses OpenAI's GPT-4o vision model to compare shoe product pages and determine which variant performs better. The system analyzes 200 URLs from an Excel file, capturing screenshots of two variants for each and generating comprehensive PDF reports with visual analysis.

## Core Architecture

The application consists of three main components:

1. **A/B Test Analyzer (`ab_test_analyzer.py`)**: Uses Playwright to capture screenshots and GPT-4o vision to analyze and compare product page variants
2. **Report Generator (`report_generator.py`)**: Creates professional PDF reports with preserved aspect ratio images and visual winner indicators
3. **Main Orchestrator (`run_ab_test.py`)**: Coordinates the analysis pipeline for batch processing of URLs

## Commands

### Running the Full Analysis
```bash
# Analyze all 200 URLs from the Excel file
python3 run_ab_test.py

# Test with first 5 URLs
python3 run_ab_test.py --test

# Custom number of URLs
python3 run_ab_test.py --limit 50

# Continue from a specific URL number
python3 run_ab_test.py --start-from 10
```

### Installation and Dependencies
```bash
# Install required packages
pip install -r requirements.txt

# Required environment variable (in .env file)
OPENAI_API_KEY=your_api_key_here

# Install Playwright browsers
playwright install chromium
```

## Report Features (Production Ready)

### Image Handling
- **Aspect ratio preserved**: No distorted images
- **Maximum dimensions**: 5.0 x 4.5 inches while maintaining proportions
- **Dynamic sizing**: Based on actual screenshot dimensions
- **Kind='proportional'**: Ensures no stretching or squashing

### Layout Design
- **One URL per page**: Clean, focused presentation
- **Landscape orientation**: Optimized for wider screenshots
- **Clean header**: URL# | Visits | Query
- **Winner announcement**: Prominent display with confidence score
- **Side-by-side screenshots**: Large, undistorted images
- **Visual indicators**: Colored borders (green=winner, red=loser, orange=tie)
- **Minimal text**: Essential analysis only

### Visual Hierarchy
1. **Top section**: Basic info (URL number, visits, query)
2. **Winner section**: Clear announcement with confidence scores
3. **Screenshots**: Main focal point with winner borders
4. **Bottom section**: Brief reasoning in small text

## Data Flow

1. **URL Loading**: Reads URLs from Excel file with visit counts
2. **Screenshot Capture**: Uses Playwright to capture both variants (A/B)
3. **Visual Analysis**: GPT-4o vision analyzes both screenshots simultaneously
4. **Winner Determination**: AI determines winner based on visual appeal and UX
5. **Report Generation**: Creates PDF with all results and visual indicators

## Key Configuration (`config.py`)

```python
# Playwright settings
BROWSER_TIMEOUT = 30000  # 30 seconds
PAGE_LOAD_TIMEOUT = 30000
SCREENSHOT_TIMEOUT = 10000

# OpenAI settings - IMPORTANT
OPENAI_MODEL = "gpt-5-mini"  # Use GPT-5-mini (released Aug 2025) for superior analysis
OPENAI_MAX_TOKENS = 1000
OPENAI_TEMPERATURE = 0.3

# Report settings
REPORT_ORIENTATION = "landscape"
MAX_IMAGE_WIDTH = 5.0  # inches
MAX_IMAGE_HEIGHT = 4.5  # inches
```

## Output Structure

```
/grouptest/
  screenshots/              # Product page screenshots
    url_XXX_variant_A_*.png
    url_XXX_variant_B_*.png
  results/                 # Analysis results
    result_XXX.json       # Individual URL analysis
    all_results.json      # Combined results
    statistics.json       # Summary statistics
  logs/                   # Execution logs
    ab_test_*.log
  ab_test_report_*.pdf    # Final PDF report
```

## Analysis Criteria

The AI evaluates variants based on:
1. **Visual Appeal**: Layout, design, use of whitespace
2. **Product Presentation**: Image quality, zoom features, multiple views
3. **Information Hierarchy**: Price visibility, key features placement
4. **Trust Signals**: Reviews, ratings, security badges
5. **Call-to-Action**: Button prominence, clarity
6. **User Experience**: Navigation ease, mobile responsiveness
7. **Special Features**: Sale indicators, shipping info, stock status

## Important Implementation Details

- Uses Playwright (faster than Selenium) for screenshot capture
- Implements retry logic with exponential backoff
- Handles cookies and popups automatically
- Preserves image aspect ratios in PDF generation
- Provides detailed logging for debugging
- All timestamps use format: YYYYMMDD_HHMMSS

## Error Handling

- **Network failures**: Automatic retry with backoff
- **Screenshot failures**: Logs error and continues with next URL
- **API rate limits**: Implements delay between requests
- **Missing data**: Gracefully handles missing URLs or variants

## Performance Optimizations

- Batch processing with progress tracking
- Reuses browser instance across captures
- Caches screenshots to avoid re-capture
- Parallel API calls where possible
- Efficient PDF generation with streaming

## Recent Updates (August 26, 2025)

- Fixed image distortion in PDF reports
- Implemented proportional image scaling
- Added visual winner indicators (colored borders)
- Optimized layout for one URL per page
- Enhanced error handling and retry logic
- Improved logging and progress tracking