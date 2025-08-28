# LEARNINGS
_Capture mistakes, solutions, and patterns. Update when: errors occur, bugs are fixed, patterns emerge._

## Claude Code Patterns & Quirks
_Common misunderstandings and how to avoid them_

### Common Claude Misunderstandings
- **File Paths**: Use absolute paths when possible, especially for WebDriver screenshots
- **Context Loss**: Claude doesn't remember previous sessions - always reference this file
- **Assumptions**: Claude may assume libraries are installed - always check requirements.txt first
- **API Keys**: Always verify .env file exists and contains required keys before running

### Commands That Work
```bash
# Run full analysis pipeline
python analyze_and_report.py

# Fetch products only (no analysis)
python api_client.py --category "schoenen" --limit 20

# Run with existing data (skip API fetch)
python analyze_and_report.py --skip-fetch

# Install dependencies
pip install -r requirements.txt
```

### Environment-Specific Quirks
_Document your environment setup and gotchas here_

- **Selenium WebDriver**: Requires Chrome installed, uses webdriver-manager for automatic driver updates
- **OpenAI API**: Requires OPENAI_API_KEY in .env file
- **WSL Users**: May need to install Chrome for Linux even if Windows Chrome exists

---

## Project-Specific Patterns
_Add patterns and solutions as you discover them_

### Beslist.nl API Patterns
- **Rate Limiting**: API seems stable, but implement retry logic for reliability
- **PIM IDs**: Not all products have PIM IDs, need to filter these out
- **Direct Match**: Returns vendors sorted by price (ascending)

### GPT-5-mini Vision Analysis
- **Model**: Using gpt-5-mini for cost-effective product page analysis
- **Screenshot Quality**: Higher resolution screenshots (1920x1080) yield better analysis results
- **Structured Output**: Always request JSON response with specific schema for consistency

### Common Errors & Solutions

#### Selenium TimeoutException
**Problem**: Page loads slower than expected
**Solution**: Increase wait timeout in product_analyzer.py:
```python
wait = WebDriverWait(driver, 20)  # Increased from 10
```

#### OpenAI API Rate Limit
**Problem**: Too many requests in short time
**Solution**: Add delay between API calls:
```python
time.sleep(1)  # Add between analyze calls
```

#### Missing Product URLs
**Problem**: Some products don't have vendor URLs
**Solution**: Check for empty vendor_urls before processing:
```python
if product.get('vendor_urls'):
    # Process product
```

---
_Last updated: 2025-08-27_