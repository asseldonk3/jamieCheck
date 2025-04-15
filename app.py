import os
import json
import requests
import datetime
from pathlib import Path
from flask import Flask, jsonify, request, send_from_directory

app = Flask(__name__)

# API URLs
PRODUCT_SEARCH_URL = "https://productsearch.api.beslist.nl/productsearch"
DIRECT_MATCH_URL = "https://productsearch.api.beslist.nl/directmatch"

# Create data directory for storing JSON files
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

@app.route('/')
def index():
    return "API is running. Use /api/products to get product data or /api/fetch to fetch fresh data."

@app.route('/data/<path:filename>')
def serve_data_file(filename):
    """Serve files from the data directory for easy inspection."""
    return send_from_directory(DATA_DIR, filename)

@app.route('/api/fetch')
def fetch_data():
    """Fetch fresh data from the Beslist.nl API and store it in JSON files."""
    # Get optional parameters from query string with defaults
    category = request.args.get('category', 'schoenen')
    limit = int(request.args.get('limit', 50))
    force_refresh = request.args.get('refresh', 'false').lower() == 'true'
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    fetch_dir = DATA_DIR / f"fetch_{timestamp}"
    fetch_dir.mkdir(exist_ok=True)
    
    try:
        # Step 1: Fetch product search data
        product_search_file = fetch_dir / "product_search.json"
        product_data = fetch_product_search_data(category, limit, product_search_file)
        
        if not product_data:
            return jsonify({"error": "Failed to fetch product search data"}), 500
        
        # Step 2: Extract products with pim3puntNullId
        result_set = extract_result_set(product_data)
        if not result_set:
            return jsonify({"error": "No result set found in product search data"}), 500
        
        products_with_pim = []
        for product in result_set:
            pim_id = product.get('pim3puntNullId')
            if pim_id:
                products_with_pim.append({
                    'pim3puntnull': pim_id,
                    'title': product.get('title', 'No title')
                })
        
        # Save products with pim to a file
        products_file = fetch_dir / "products_with_pim.json"
        with open(products_file, 'w') as f:
            json.dump(products_with_pim, f, indent=2)
        
        # Step 3: Fetch direct match data for each product
        direct_match_dir = fetch_dir / "direct_matches"
        direct_match_dir.mkdir(exist_ok=True)
        
        for product in products_with_pim:
            pim_id = product['pim3puntnull']
            direct_match_file = direct_match_dir / f"{pim_id}.json"
            
            # Fetch direct match data
            direct_match_data = fetch_direct_match_data(pim_id, direct_match_file)
            
            if direct_match_data:
                # Extract and add URLs to the product
                urls = extract_direct_match_urls(direct_match_data)
                product['direct_match_urls'] = urls
        
        # Step 4: Generate the final result JSON
        final_result = []
        for product in products_with_pim:
            result_item = {
                'pim3puntnull': product['pim3puntnull'],
                'product_url': f"https://www.beslist.nl/p/schoenen/{product['pim3puntnull']}/"
            }
            
            # Add direct match URLs
            for i, url in enumerate(product.get('direct_match_urls', [])[:3], 1):
                result_item[f"url{i}"] = url
            
            final_result.append(result_item)
        
        # Save final result
        final_result_file = fetch_dir / "final_result.json"
        with open(final_result_file, 'w') as f:
            json.dump(final_result, f, indent=2)
        
        # Also save to a predictable location for the API
        latest_result_file = DATA_DIR / "latest_result.json"
        with open(latest_result_file, 'w') as f:
            json.dump(final_result, f, indent=2)
        
        return jsonify({
            "message": "Data fetch completed successfully",
            "fetch_directory": str(fetch_dir),
            "product_count": len(result_set),
            "products_with_pim": len(products_with_pim),
            "final_result_count": len(final_result),
            "files": {
                "product_search": f"/data/fetch_{timestamp}/product_search.json",
                "products_with_pim": f"/data/fetch_{timestamp}/products_with_pim.json",
                "final_result": f"/data/fetch_{timestamp}/final_result.json",
                "latest_result": "/data/latest_result.json"
            }
        })
    
    except Exception as e:
        return jsonify({"error": f"Error fetching data: {str(e)}"}), 500

@app.route('/api/products')
def get_products():
    """Return the latest processed product data."""
    latest_result_file = DATA_DIR / "latest_result.json"
    
    # If no data has been fetched yet, fetch it
    if not latest_result_file.exists():
        return fetch_data()
    
    try:
        with open(latest_result_file, 'r') as f:
            result = json.load(f)
        return jsonify(result)
    
    except Exception as e:
        return jsonify({"error": f"Error loading product data: {str(e)}"}), 500

@app.route('/api/product/<pim_id>')
def get_product(pim_id):
    """Get direct match URLs for a specific pim3puntnull ID."""
    try:
        # Check if we have cached data for this pim_id
        latest_result_file = DATA_DIR / "latest_result.json"
        
        if latest_result_file.exists():
            with open(latest_result_file, 'r') as f:
                all_products = json.load(f)
                
            # Find the product with the specified pim_id
            for product in all_products:
                if product.get('pim3puntnull') == pim_id:
                    return jsonify(product)
        
        # If not found in cache or no cache exists, fetch fresh data
        direct_match_file = DATA_DIR / f"direct_match_{pim_id}.json"
        direct_match_data = fetch_direct_match_data(pim_id, direct_match_file)
        
        if not direct_match_data:
            return jsonify({"error": "Failed to fetch direct match data"}), 500
        
        urls = extract_direct_match_urls(direct_match_data)
        
        result = {
            "pim3puntnull": pim_id,
            "product_url": f"https://www.beslist.nl/p/schoenen/{pim_id}/"
        }
        
        # Add URLs with indices
        for i, url in enumerate(urls[:3], 1):
            result[f"url{i}"] = url
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({"error": f"Error processing product: {str(e)}"}), 500

def fetch_product_search_data(category, limit, output_file):
    """Fetch product search data from Beslist.nl API and save to file."""
    # Parameters for the product search API
    params = {
        "country": "nl",
        "cat_url": f"/{category}/",
        "sort": "popularity",
        "sortdirection": "desc",
        "limit": limit,
        "offset": 0,
        "res[or]": "true",
        "res[facets]": "false",
        "res[facets_all]": 0,
        "res[facets_selected]": "false",
        "res[stats]": "true",
        "res[categories]": "true",
        "res[collapse]": "true",
        "res[category_direction_markers]": "true",
        "splittestid": 9
    }
    
    try:
        # Make the API call
        response = requests.get(PRODUCT_SEARCH_URL, params=params)
        response.raise_for_status()
        data = response.json()
        
        # Save to file
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        return data
    
    except Exception as e:
        print(f"Error fetching product search data: {str(e)}")
        return None

def fetch_direct_match_data(pim_id, output_file):
    """Fetch direct match data for a specific pim3puntnull ID and save to file."""
    params = {
        "pim3puntNullId": pim_id,
        "country": "nl",
        "limit": 3,
        "splittestid": 1,
        "sort": "price",
        "sortdirection": "desc"
    }
    
    try:
        # Make the API call
        response = requests.get(DIRECT_MATCH_URL, params=params)
        response.raise_for_status()
        data = response.json()
        
        # Save to file
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        return data
    
    except Exception as e:
        print(f"Error fetching direct match data for {pim_id}: {str(e)}")
        return None

def extract_result_set(data):
    """Extract the result set from the product search data."""
    if not data.get('results') or not isinstance(data['results'], list) or not data['results'][0].get('resultSet'):
        return None
    
    return data['results'][0]['resultSet']

def extract_direct_match_urls(data):
    """Extract URLs from the direct match data."""
    urls = []
    
    # Check for valid response structure
    if not data.get('results') or not isinstance(data['results'], list) or not data['results'][0].get('resultSet'):
        return urls
    
    # Get resultSet from the response
    result_set = data['results'][0]['resultSet']
    
    # Extract URLs from the resultSet
    for item in result_set:
        if item.get('shopItem') and item['shopItem'].get('url'):
            urls.append(item['shopItem']['url'])
    
    return urls

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True) 