# Beslist.nl Product API

This Flask application fetches product data from Beslist.nl API, extracts pim3puntNullId values, retrieves direct match URLs for each product, and stores all data in JSON files.

## Features

- Fetches product data from Beslist.nl productsearch API
- Stores all API responses in JSON files for easy inspection and debugging
- For each product with a pim3puntNullId, makes additional API calls to get direct match URLs
- Returns processed data in JSON format with the product URL and up to 3 direct match URLs
- Caches results for faster access

## Setup

1. Create a virtual environment (optional but recommended):
   ```
   python -m venv .venv
   ```

2. Activate the virtual environment:
   - Windows: `.venv\Scripts\activate`
   - macOS/Linux: `source .venv/bin/activate`

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Run the application:
   ```
   python app.py
   ```

## API Endpoints

- `GET /` - Simple check to ensure the API is running
- `GET /api/fetch` - Fetches fresh data from the Beslist.nl API and stores it in JSON files
  - Optional query parameters:
    - `category`: Category name (default: `schoenen`)
    - `limit`: Number of products to fetch (default: 50)
    - `refresh`: Whether to force a refresh of data (default: false)
- `GET /api/products` - Returns the latest processed product data
- `GET /api/product/<pim_id>` - Get direct match URLs for a specific pim3puntNullId
- `GET /data/<filename>` - Access stored JSON files directly

## Data Storage

All data is stored in a `data` directory:
- `data/fetch_TIMESTAMP/` - A directory for each fetch operation containing:
  - `product_search.json` - Raw response from the product search API
  - `products_with_pim.json` - Extracted products with pim3puntNullId
  - `direct_matches/` - Directory with individual responses for each direct match API call
  - `final_result.json` - The final processed result
- `data/latest_result.json` - The latest processed result (used by the API)

## Response Format

The `/api/products` endpoint returns data in the following format:

```json
[
  {
    "pim3puntnull": "nl-nl-gold-0088300601400",
    "product_url": "https://www.beslist.nl/p/schoenen/nl-nl-gold-0088300601400/",
    "url1": "https://www.directmatch1.com/product",
    "url2": "https://www.directmatch2.com/product",
    "url3": "https://www.directmatch3.com/product"
  },
  {
    "pim3puntnull": "nl-nl-gold-4260286381620",
    "product_url": "https://www.beslist.nl/p/schoenen/nl-nl-gold-4260286381620/",
    "url1": "https://www.directmatch1.com/product2",
    "url2": "https://www.directmatch2.com/product2"
  }
]
```

## Testing

The repository includes a `check_api.py` script that can be used to test the API response structure and verify that the application is working correctly.

```
python check_api.py
```

This will generate a `final_results.json` file with sample data from the API. 