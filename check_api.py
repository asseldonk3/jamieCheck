import requests
import json

def check_product_search_api():
    """Test the initial product search API and print the JSON structure."""
    print("Testing the product search API...")
    
    # Parameters for the product search API
    params = {
        "country": "nl",
        "cat_url": "/schoenen/",
        "sort": "popularity",
        "sortdirection": "desc",
        "limit": 50,
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
        print("Making request to product search API...")
        response = requests.get(
            "https://productsearch.api.beslist.nl/productsearch", 
            params=params
        )
        response.raise_for_status()
        data = response.json()
        
        # Navigate to resultSet
        if not data.get('results') or not isinstance(data['results'], list) or not data['results'][0].get('resultSet'):
            print("Unexpected API response structure. Couldn't find results or resultSet.")
            return
            
        result_set = data['results'][0]['resultSet']
        print(f"Found {len(result_set)} products in resultSet")
        
        # Process products and find pim3puntnull IDs
        products_with_pim3null = []
        
        for i, product in enumerate(result_set[:10]):  # Look at first 10 products
            pim3null_id = product.get('pim3puntNullId')
            if pim3null_id:
                print(f"Product {i+1}: Found pim3puntNullId: {pim3null_id}")
                
                # Store product info
                product_info = {
                    'pim3puntnull': pim3null_id,
                    'title': product.get('title', 'No title'),
                    'shop_url': None
                }
                
                # Check if there's a shop URL in the product data
                if product.get('shopItem') and product['shopItem'].get('url'):
                    product_info['shop_url'] = product['shopItem']['url']
                    print(f"  Shop URL found in product data: {product_info['shop_url']}")
                
                products_with_pim3null.append(product_info)
            else:
                print(f"Product {i+1}: No pim3puntNullId found")
        
        # Process products with pim3null IDs
        print(f"\nFound {len(products_with_pim3null)} products with pim3puntNullId")
        
        final_results = []
        
        # Test the directmatch API for a few products
        for i, product in enumerate(products_with_pim3null[:3]):
            print(f"\nProcessing product {i+1}: {product['title']}")
            print(f"pim3puntnull: {product['pim3puntnull']}")
            
            # Get direct match results
            direct_match_results = get_direct_match_urls(product['pim3puntnull'])
            
            # Add direct match URLs to product info
            result = {
                'pim3puntnull': product['pim3puntnull'],
            }
            
            # Add original shop URL if available
            if product['shop_url']:
                result['original_shop_url'] = product['shop_url']
            
            # Add direct match URLs
            for j, url in enumerate(direct_match_results[:3], 1):
                result[f'url{j}'] = url
                print(f"  url{j}: {url}")
            
            final_results.append(result)
        
        # Save final results to file
        with open('final_results.json', 'w') as f:
            json.dump(final_results, f, indent=2)
        print("\nFinal results saved to 'final_results.json'")
        
    except requests.RequestException as e:
        print(f"API request error: {str(e)}")
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()

def get_direct_match_urls(pim3punt_null_id):
    """Get URLs from the direct match API for a specific pim3puntnull ID."""
    print(f"Making direct match API request for ID: {pim3punt_null_id}")
    
    params = {
        "pim3puntNullId": pim3punt_null_id,
        "country": "nl",
        "limit": 3,
        "splittestid": 1,
        "sort": "price",
        "sortdirection": "desc"
    }
    
    try:
        # Make the API call
        response = requests.get(
            "https://productsearch.api.beslist.nl/directmatch", 
            params=params
        )
        response.raise_for_status()
        data = response.json()
        
        # Check for results
        if not data.get('results') or not isinstance(data['results'], list) or not data['results'][0].get('resultSet'):
            print("  No valid results found in direct match response")
            return []
            
        # Get resultSet from the response
        result_set = data['results'][0]['resultSet']
        print(f"  Found {len(result_set)} items in direct match resultSet")
        
        # Extract URLs
        urls = []
        for item in result_set:
            if item.get('shopItem') and item['shopItem'].get('url'):
                urls.append(item['shopItem']['url'])
        
        print(f"  Extracted {len(urls)} URLs from direct match response")
        return urls
        
    except requests.RequestException as e:
        print(f"  Direct match API request error: {str(e)}")
        return []
    except Exception as e:
        print(f"  Unexpected error in direct match API: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

if __name__ == "__main__":
    check_product_search_api() 