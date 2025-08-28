# PROJECT INDEX
_Project structure and technical specs. Update when: creating files, adding dependencies, defining schemas._

## Stack
- **Language**: Python 3.x
- **AI Model**: OpenAI GPT-5-mini (vision + text)
- **Web Scraping**: Selenium WebDriver with Chrome
- **PDF Generation**: ReportLab
- **API Client**: Requests library
- **Data Source**: Beslist.nl Affiliate API

## Directory Structure
```
jamieCheck/
  cc1/                → CC1 documentation system
    TASKS.md         → Active task tracking
    LEARNINGS.md     → Knowledge capture
    PROJECT_INDEX.md → This file
    BACKLOG.md       → Future planning
  
  data/              → API data storage
    fetch_*/         → Timestamped fetch results
    latest_result.json → Most recent data
  
  analysis_results/  → Analysis outputs
    analysis_*/      → Timestamped analysis runs
      screenshots/   → Product page screenshots
      results/       → Individual JSON analyses
      *.pdf          → Generated reports
  
  input/             → Input data directory
  grouptest/         → Test group data
  
  .venv/             → Python virtual environment
  .env               → Environment variables (API keys)
  
  # Core Python Files
  analyze_and_report.py → Main orchestrator
  api_client.py      → Beslist API interface
  product_analyzer.py → Screenshot & AI analysis
  config.py          → Configuration settings
  
  # Documentation
  README.md          → Project overview
  CLAUDE.md          → Claude Code instructions
  requirements.txt   → Python dependencies
```

## Database Schema
_No database currently - uses JSON file storage_

## API Endpoints
### Beslist.nl Product Search API
- **Endpoint**: `https://productsearch.api.beslist.nl/productsearch`
- **Method**: GET
- **Required Params**: 
  - `country`: "nl"
  - `category`: product category
  - `limit`: max results

### Beslist.nl Direct Match API
- **Endpoint**: `https://productsearch.api.beslist.nl/directmatch`
- **Method**: GET
- **Required Params**:
  - `country`: "nl"
  - `pim_id`: product ID
  - `limit`: max vendor results
  - `sort`: "price_asc"

## Core Files

### Configuration
- `.env` - Contains OPENAI_API_KEY
- `config.py` - Application settings:
  - DEFAULT_CATEGORY = "mode"
  - DEFAULT_LIMIT = 50
  - DIRECT_MATCH_LIMIT = 3

### Main Components
- **analyze_and_report.py**: Coordinates entire pipeline, generates PDF reports
- **api_client.py**: Handles all Beslist.nl API interactions
- **product_analyzer.py**: WebDriver screenshot capture + GPT-5-mini analysis

### Data Flow
1. `api_client.py` → Fetches products → `data/fetch_*/`
2. `product_analyzer.py` → Captures screenshots → `analysis_results/*/screenshots/`
3. GPT-5-mini → Analyzes screenshots → `analysis_results/*/results/`
4. `analyze_and_report.py` → Generates PDF → `analysis_results/*/product_analysis_report_*.pdf`

## Dependencies
### Major Libraries
- `openai>=1.0.0` - GPT-5-mini API access
- `selenium>=4.0.0` - Web scraping
- `webdriver-manager` - Chrome driver management
- `reportlab` - PDF generation
- `Pillow` - Image processing
- `requests` - HTTP client
- `python-dotenv` - Environment variables

### System Requirements
- Chrome browser installed
- Python 3.7+
- Internet connection for API access

## Key Decisions
1. **GPT-5-mini over GPT-4V**: Better cost/performance for structured extraction
2. **Selenium over BeautifulSoup**: JavaScript-rendered pages require browser
3. **JSON File Storage**: Simple, no database overhead for current scale
4. **Timestamped Directories**: Easy tracking of historical runs
5. **3 Vendor Limit**: Balance between data completeness and API usage

## Recent Changes
- Migrated from GPT-4 to GPT-5-mini (faster, cheaper)
- Added CC1 documentation system for cross-session memory
- Implemented retry logic for web scraping stability

---
_Last updated: 2025-08-27_