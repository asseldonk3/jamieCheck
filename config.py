"""
Configuration settings for the Beslist.nl API client.
Edit this file to change default settings without modifying the main code.
"""

# Default category to use for API requests
DEFAULT_CATEGORY = "schoenen"

# Default number of products to fetch
DEFAULT_LIMIT = 50

# Base URL format for product URLs
# Use {category} as placeholder for the category and {pim_id} for the product ID
PRODUCT_URL_FORMAT = "https://www.beslist.nl/p/products/{category}/{pim_id}/"

# API endpoints
PRODUCT_SEARCH_URL = "https://productsearch.api.beslist.nl/productsearch"
DIRECT_MATCH_URL = "https://productsearch.api.beslist.nl/directmatch"

# Default output directory
DEFAULT_OUTPUT_DIR = "data"

# Direct match API sort settings
DIRECT_MATCH_SORT = "price"  # Sort by price
DIRECT_MATCH_SORT_DIRECTION = "asc"  # "asc" for lowest first, "desc" for highest first
DIRECT_MATCH_LIMIT = 3  # Number of matches to return 