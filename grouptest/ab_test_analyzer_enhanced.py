"""
Enhanced A/B Test Analyzer with Duplicate Detection
Compares opt_seg=5 vs opt_seg=6 ranking algorithms with specific focus on duplicate products
"""

import os
import sys
import json
import time
import base64
import logging
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
import hashlib

import pandas as pd
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from bs4 import BeautifulSoup
import dotenv

# Add parent directory to path to import existing modules
sys.path.append(str(Path(__file__).parent.parent))

import config

# Load environment variables
dotenv.load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config.LOGS_DIR / f"ab_test_enhanced_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class EnhancedABTestAnalyzer:
    """Enhanced analyzer with duplicate detection"""
    
    def __init__(self):
        self.driver = None
        self.results = []
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        
        if not self.openai_api_key:
            logger.error("OPENAI_API_KEY not found in environment variables")
            raise ValueError("OPENAI_API_KEY is required for analysis")
        
        # Create necessary directories
        config.SCREENSHOTS_DIR.mkdir(exist_ok=True, parents=True)
        config.RESULTS_DIR.mkdir(exist_ok=True, parents=True)
        config.LOGS_DIR.mkdir(exist_ok=True, parents=True)
        
        logger.info("EnhancedABTestAnalyzer initialized")
    
    def setup_driver(self):
        """Initialize Selenium WebDriver with optimal settings"""
        if self.driver:
            return
            
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument(f'--window-size={config.WINDOW_WIDTH},{config.WINDOW_HEIGHT}')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        try:
            self.driver = webdriver.Chrome(options=options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            logger.info("WebDriver initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize WebDriver: {e}")
            raise
    
    def close_driver(self):
        """Close the WebDriver"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("WebDriver closed")
            except Exception as e:
                logger.warning(f"Error closing WebDriver: {e}")
            finally:
                self.driver = None
    
    def modify_url_with_param(self, base_url, param):
        """Modify URL to include opt_seg parameter"""
        parsed = urlparse(base_url)
        query_params = parse_qs(parsed.query)
        query_params['opt_seg'] = [param]
        new_query = urlencode(query_params, doseq=True)
        return urlunparse(parsed._replace(query=new_query))
    
    def capture_screenshot(self, url, variant_name, url_index):
        """Capture screenshot and extract page data"""
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Capturing {variant_name} for URL {url_index}: {url[:80]}...")
                
                self.driver.get(url)
                time.sleep(3)  # Wait for page to load
                
                # Try to close cookie banner
                try:
                    cookie_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Accepteren') or contains(text(), 'Accept')]")
                    cookie_button.click()
                    time.sleep(1)
                except:
                    pass
                
                # Take screenshot
                url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
                screenshot_filename = f"url_{url_index:03d}_{variant_name}_{url_hash}.png"
                screenshot_path = config.SCREENSHOTS_DIR / screenshot_filename
                self.driver.save_screenshot(str(screenshot_path))
                
                logger.info(f"Screenshot saved: {screenshot_filename}")
                
                # Extract page data
                page_data = self.extract_page_data()
                
                return {
                    'filename': screenshot_filename,
                    'screenshot_path': screenshot_path,
                    'h1_title': page_data.get('h1_title'),
                    'product_count': page_data.get('product_count'),
                    'product_titles': page_data.get('product_titles', [])
                }
                
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    logger.error(f"Failed to capture {variant_name} after {max_retries} attempts")
                    return None
                time.sleep(2)
    
    def extract_page_data(self):
        """Extract product data from the current page"""
        try:
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Extract H1 title
            h1_element = soup.find('h1')
            h1_title = h1_element.get_text(strip=True) if h1_element else "No H1 found"
            
            # Extract product titles (first 8-10 products)
            product_titles = []
            product_selectors = [
                "article h3", "article h2",
                ".product-title", ".product-name",
                "[data-test='product-title']",
                ".card__title", ".item-title"
            ]
            
            for selector in product_selectors:
                products = soup.select(selector)
                if products:
                    product_titles = [p.get_text(strip=True) for p in products[:10]]
                    break
            
            return {
                'h1_title': h1_title,
                'product_count': len(product_titles),
                'product_titles': product_titles
            }
            
        except Exception as e:
            logger.error(f"Error extracting page data: {e}")
            return {
                'h1_title': "Error extracting",
                'product_count': 0,
                'product_titles': []
            }
    
    def analyze_with_enhanced_gpt(self, variant_a_data, variant_b_data):
        """Enhanced GPT analysis with duplicate detection"""
        
        # Prepare images for GPT
        def encode_image(image_path):
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        
        # Enhanced prompt with duplicate detection
        prompt = f"""
        You are an expert in e-commerce product ranking algorithms. Your task has TWO INDEPENDENT parts:
        
        PART 1 - RANKING QUALITY (determines winner):
        Evaluate which algorithm (A or B) produces better product rankings based on:
        - Relevance to search query: {variant_a_data.get('h1_title', 'Unknown')}
        - Product diversity and variety
        - Quality of top results
        - User value (better deals, ratings, popular items first)
        
        PART 2 - DUPLICATE DETECTION (supplementary information only):
        Count duplicate products - these are items with the EXACT SAME product image appearing multiple times.
        A duplicate = identical product photo from different sellers (same item, different shops).
        Do NOT count different colors, sizes, or models as duplicates.
        
        Return ONLY a valid JSON object:
        {{
            "winner": "A", "B", or "Tie" (based on ranking quality, NOT duplicates),
            "confidence": <number 0.5-1.0>,
            "score_a": <number 1-10> (ranking quality score),
            "score_b": <number 1-10> (ranking quality score),
            "reasoning": "Why this version has better rankings (ignore duplicates here)",
            "key_differences": "Main ranking quality difference",
            "duplicates_in_a": <count of products with identical images in first 8 of A>,
            "duplicates_in_b": <count of products with identical images in first 8 of B>,
            "unique_products_a": <count of products with unique images in first 8 of A>,
            "unique_products_b": <count of products with unique images in first 8 of B>,
            "duplicate_notes": "Brief note about duplicate patterns observed"
        }}
        """
        
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.openai_api_key}"
            }
            
            # Encode images
            image_a_base64 = encode_image(variant_a_data['screenshot_path'])
            image_b_base64 = encode_image(variant_b_data['screenshot_path'])
            
            payload = {
                "model": "gpt-5-mini",  # Using GPT-5-mini for duplicate detection analysis
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an e-commerce ranking expert. Carefully analyze both screenshots for duplicate products - these are products with the EXACT SAME product image appearing multiple times (same item from different sellers). Look for identical product photos, not just similar names. Count duplicates accurately and evaluate how they impact user experience."
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_a_base64}",
                                    "detail": "high"  # Use high detail for better duplicate detection
                                }
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_b_base64}",
                                    "detail": "high"  # Use high detail for better duplicate detection
                                }
                            }
                        ]
                    }
                ],
                "max_completion_tokens": 4000  # Further increased for complex pages
            }
            
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    analysis = json.loads(result['choices'][0]['message']['content'])
                    logger.info(f"Enhanced GPT analysis completed: Winner={analysis.get('winner')}, "
                              f"Duplicates A={analysis.get('duplicates_in_a')}, B={analysis.get('duplicates_in_b')}")
                    return analysis
                except (json.JSONDecodeError, KeyError) as parse_error:
                    logger.error(f"Failed to parse API response: {parse_error}")
                    logger.error(f"Raw response: {response.text[:500]}")
                    return None
            else:
                logger.error(f"GPT API error: {response.status_code} - {response.text[:500]}")
                return None
                
        except Exception as e:
            logger.error(f"Error in enhanced GPT analysis: {e}")
            return None
    
    def process_url(self, url, url_index, visits=0):
        """Process a single URL with both variants"""
        
        # Create variant URLs
        url_a = self.modify_url_with_param(url, config.VARIANT_A_PARAM)
        url_b = self.modify_url_with_param(url, config.VARIANT_B_PARAM)
        
        # Capture screenshots
        variant_a_data = self.capture_screenshot(url_a, "variant_A", url_index)
        variant_b_data = self.capture_screenshot(url_b, "variant_B", url_index)
        
        if not variant_a_data or not variant_b_data:
            logger.warning(f"Skipping URL {url_index} due to capture failure")
            return None
        
        # Analyze with enhanced GPT
        analysis = self.analyze_with_enhanced_gpt(variant_a_data, variant_b_data)
        
        if not analysis:
            logger.warning(f"Enhanced GPT analysis failed for URL {url_index}")
            analysis = {
                "winner": "unknown",
                "confidence": 0.5,
                "score_a": 0,
                "score_b": 0,
                "duplicates_in_a": -1,
                "duplicates_in_b": -1,
                "unique_products_a": -1,
                "unique_products_b": -1,
                "duplicate_impact": "Unable to analyze",
                "reasoning": "Analysis failed",
                "key_differences": "Unable to analyze"
            }
        
        # Compile enhanced results
        result = {
            "url_index": url_index,
            "original_url": url,
            "visits": visits,
            "variant_a": {
                "url": url_a,
                "screenshot": variant_a_data['filename'],
                "h1_title": variant_a_data.get('h1_title'),
                "product_count": variant_a_data.get('product_count'),
                "score": analysis.get('score_a', 0),
                "duplicates": analysis.get('duplicates_in_a', -1),
                "unique_products": analysis.get('unique_products_a', -1)
            },
            "variant_b": {
                "url": url_b,
                "screenshot": variant_b_data['filename'],
                "h1_title": variant_b_data.get('h1_title'),
                "product_count": variant_b_data.get('product_count'),
                "score": analysis.get('score_b', 0),
                "duplicates": analysis.get('duplicates_in_b', -1),
                "unique_products": analysis.get('unique_products_b', -1)
            },
            "analysis": {
                "winner": analysis.get('winner'),
                "confidence": analysis.get('confidence', 0.5),
                "reasoning": analysis.get('reasoning'),
                "key_differences": analysis.get('key_differences'),
                "duplicate_notes": analysis.get('duplicate_notes', ''),
                "duplicates_comparison": f"A has {analysis.get('duplicates_in_a', -1)} duplicates, B has {analysis.get('duplicates_in_b', -1)} duplicates"
            }
        }
        
        # Save individual result
        result_file = config.RESULTS_DIR / f"enhanced_result_{url_index:03d}.json"
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        return result
    
    def run_analysis(self, limit=10, start_from=None):
        """Run the enhanced analysis"""
        
        logger.info("Starting enhanced A/B test analysis with duplicate detection")
        
        # Load URLs from Excel
        try:
            df = pd.read_excel(config.INPUT_FILE)
            logger.info(f"Loaded {len(df)} URLs from Excel")
        except Exception as e:
            logger.error(f"Failed to load Excel file: {e}")
            raise
        
        # Apply start_from if specified
        if start_from and start_from > 1:
            df = df.iloc[start_from-1:]
            logger.info(f"Starting from URL {start_from}")
        
        # Limit processing
        df = df.head(limit)
        logger.info(f"Processing limited to {limit} URLs for enhanced analysis")
        
        # Setup WebDriver
        self.setup_driver()
        
        try:
            # Process each URL
            for index, row in df.iterrows():
                url = row['url']
                visits = row.get('visits', 0)
                url_index = index + 1
                
                logger.info(f"Processing URL {url_index}/{len(df)}")
                
                result = self.process_url(url, url_index, visits)
                if result:
                    self.results.append(result)
                
                # Save intermediate results
                if url_index % 5 == 0:
                    self.save_results()
                    logger.info(f"Intermediate save: {url_index} URLs processed")
            
            # Save final results
            self.save_results()
            logger.info(f"Enhanced analysis complete: {len(self.results)} URLs processed")
            
            # Calculate enhanced statistics
            self.calculate_enhanced_statistics()
            
        finally:
            self.close_driver()
        
        return self.results
    
    def save_results(self):
        """Save enhanced results"""
        results_file = config.RESULTS_DIR / "enhanced_results.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        logger.info(f"Enhanced results saved to {results_file}")
    
    def calculate_enhanced_statistics(self):
        """Calculate statistics including duplicate analysis"""
        
        if not self.results:
            logger.warning("No results to calculate statistics")
            return
        
        # Basic statistics
        wins_a = sum(1 for r in self.results if r['analysis']['winner'] == 'A')
        wins_b = sum(1 for r in self.results if r['analysis']['winner'] == 'B')
        ties = sum(1 for r in self.results if r['analysis']['winner'] == 'Tie')
        
        # Duplicate statistics
        total_duplicates_a = sum(r['variant_a'].get('duplicates', 0) for r in self.results if r['variant_a'].get('duplicates', -1) >= 0)
        total_duplicates_b = sum(r['variant_b'].get('duplicates', 0) for r in self.results if r['variant_b'].get('duplicates', -1) >= 0)
        avg_duplicates_a = total_duplicates_a / len(self.results) if self.results else 0
        avg_duplicates_b = total_duplicates_b / len(self.results) if self.results else 0
        
        # Unique products statistics
        avg_unique_a = sum(r['variant_a'].get('unique_products', 0) for r in self.results) / len(self.results) if self.results else 0
        avg_unique_b = sum(r['variant_b'].get('unique_products', 0) for r in self.results) / len(self.results) if self.results else 0
        
        stats = {
            "total_urls": len(self.results),
            "variant_a_wins": wins_a,
            "variant_b_wins": wins_b,
            "ties": ties,
            "win_percentage_a": round(wins_a / len(self.results) * 100, 1),
            "win_percentage_b": round(wins_b / len(self.results) * 100, 1),
            "average_duplicates_a": round(avg_duplicates_a, 2),
            "average_duplicates_b": round(avg_duplicates_b, 2),
            "total_duplicates_a": total_duplicates_a,
            "total_duplicates_b": total_duplicates_b,
            "average_unique_products_a": round(avg_unique_a, 2),
            "average_unique_products_b": round(avg_unique_b, 2),
            "duplicate_difference": round(avg_duplicates_b - avg_duplicates_a, 2),
            "overall_winner": "A (opt_seg=5)" if wins_a > wins_b else "B (opt_seg=6)" if wins_b > wins_a else "Tie"
        }
        
        # Save statistics
        stats_file = config.RESULTS_DIR / "enhanced_statistics.json"
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        
        logger.info("=" * 60)
        logger.info("ENHANCED ANALYSIS STATISTICS")
        logger.info("=" * 60)
        logger.info(f"Total URLs analyzed: {stats['total_urls']}")
        logger.info(f"Winner distribution: A={wins_a}, B={wins_b}, Tie={ties}")
        logger.info(f"Average duplicates in A: {stats['average_duplicates_a']}")
        logger.info(f"Average duplicates in B: {stats['average_duplicates_b']}")
        logger.info(f"Average unique products in A: {stats['average_unique_products_a']}")
        logger.info(f"Average unique products in B: {stats['average_unique_products_b']}")
        logger.info(f"Duplicate difference (B-A): {stats['duplicate_difference']}")
        logger.info("=" * 60)
        
        return stats


def main():
    """Main execution for enhanced analysis"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Enhanced A/B test analysis with duplicate detection')
    parser.add_argument('--limit', type=int, default=10, help='Number of URLs to process')
    parser.add_argument('--start-from', type=int, help='URL index to start from')
    
    args = parser.parse_args()
    
    analyzer = EnhancedABTestAnalyzer()
    results = analyzer.run_analysis(limit=args.limit, start_from=args.start_from)
    
    print(f"\nEnhanced analysis complete: {len(results)} URLs processed")
    print("Check results/enhanced_results.json for detailed duplicate analysis")


if __name__ == "__main__":
    main()