import requests
import json
from pathlib import Path
import datetime
import argparse
import sys
import config

# API URLs imported from config
PRODUCT_SEARCH_URL = config.PRODUCT_SEARCH_URL
DIRECT_MATCH_URL = config.DIRECT_MATCH_URL

def fetch_product_search_data(category, limit, output_file):
    """Fetch product search data from Beslist.nl API and save to file."""
    # Parameters for the product search API
    params = {
        "country": "nl",
        "cat_url": category,
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
        "limit": config.DIRECT_MATCH_LIMIT,
        "splittestid": 1,
        "sort": config.DIRECT_MATCH_SORT,
        "sortdirection": config.DIRECT_MATCH_SORT_DIRECTION
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

def format_product_url(pim_id, category):
    """Format the product URL using the configured pattern."""
    return config.PRODUCT_URL_FORMAT.format(category=category, pim_id=pim_id)

def fetch_and_process_data(category, limit, data_dir):
    """Fetch data from APIs and create the final JSON result."""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    fetch_dir = data_dir / f"fetch_{timestamp}"
    fetch_dir.mkdir(exist_ok=True)
    
    try:
        # Step 1: Fetch product search data
        product_search_file = fetch_dir / "product_search.json"
        product_data = fetch_product_search_data(category, limit, product_search_file)
        
        if not product_data:
            return {"error": "Failed to fetch product search data"}, None
        
        # Step 2: Extract products with pim3puntNullId
        result_set = extract_result_set(product_data)
        if not result_set:
            return {"error": "No result set found in product search data"}, None
        
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
                'product_url': format_product_url(product['pim3puntnull'], category)
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
        latest_result_file = data_dir / "latest_result.json"
        with open(latest_result_file, 'w') as f:
            json.dump(final_result, f, indent=2)
        
        fetch_info = {
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
        }
        
        return fetch_info, final_result
    
    except Exception as e:
        return {"error": f"Error fetching data: {str(e)}"}, None

def get_product_by_pim_id(pim_id, category, data_dir):
    """Get product data for a specific pim_id, either from cache or by fetching fresh data."""
    try:
        # Check if we have cached data for this pim_id
        latest_result_file = data_dir / "latest_result.json"
        
        if latest_result_file.exists():
            with open(latest_result_file, 'r') as f:
                all_products = json.load(f)
                
            # Find the product with the specified pim_id
            for product in all_products:
                if product.get('pim3puntnull') == pim_id:
                    return product, None
        
        # If not found in cache or no cache exists, fetch fresh data
        direct_match_file = data_dir / f"direct_match_{pim_id}.json"
        direct_match_data = fetch_direct_match_data(pim_id, direct_match_file)
        
        if not direct_match_data:
            return None, "Failed to fetch direct match data"
        
        urls = extract_direct_match_urls(direct_match_data)
        
        result = {
            "pim3puntnull": pim_id,
            "product_url": format_product_url(pim_id, category)
        }
        
        # Add URLs with indices
        for i, url in enumerate(urls[:3], 1):
            result[f"url{i}"] = url
        
        return result, None
    
    except Exception as e:
        return None, f"Error processing product: {str(e)}"

def main():
    """Main function to run the script from command line."""
    parser = argparse.ArgumentParser(description='Fetch product data from Beslist.nl API')
    parser.add_argument('--category', type=str, default=config.DEFAULT_CATEGORY, 
                        help=f'Product category (default: {config.DEFAULT_CATEGORY})')
    parser.add_argument('--limit', type=int, default=config.DEFAULT_LIMIT, 
                        help=f'Number of products to fetch (default: {config.DEFAULT_LIMIT})')
    parser.add_argument('--output-dir', type=str, default=config.DEFAULT_OUTPUT_DIR, 
                        help=f'Directory to store output files (default: {config.DEFAULT_OUTPUT_DIR})')
    parser.add_argument('--pim-id', type=str, help='Specific pim3puntnull ID to fetch (optional)')
    
    args = parser.parse_args()
    
    # Create data directory if it doesn't exist
    data_dir = Path(args.output_dir)
    data_dir.mkdir(exist_ok=True)
    
    if args.pim_id:
        # Fetch data for a specific pim_id
        print(f"Fetching data for pim3puntnull ID: {args.pim_id}")
        product, error = get_product_by_pim_id(args.pim_id, args.category, data_dir)
        
        if error:
            print(f"Error: {error}")
            sys.exit(1)
        
        print(f"Product data for {args.pim_id}:")
        print(json.dumps(product, indent=2))
    else:
        # Fetch and process all data
        print(f"Fetching product data for category: {args.category}, limit: {args.limit}")
        fetch_info, final_result = fetch_and_process_data(args.category, args.limit, data_dir)
        
        if "error" in fetch_info:
            print(f"Error: {fetch_info['error']}")
            sys.exit(1)
        
        print(f"Successfully fetched and processed data:")
        print(f"  - Products found: {fetch_info['product_count']}")
        print(f"  - Products with pim3puntnull ID: {fetch_info['products_with_pim']}")
        print(f"  - Final result count: {fetch_info['final_result_count']}")
        print(f"  - Data stored in: {fetch_info['fetch_directory']}")
        print(f"  - Latest result saved to: {data_dir / 'latest_result.json'}")

if __name__ == "__main__":
    main()