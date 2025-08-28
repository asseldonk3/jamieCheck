"""
A/B Test Analyzer for Product Ranking Comparison
Compares opt_seg=5 vs opt_seg=6 ranking algorithms
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
        logging.FileHandler(config.LOGS_DIR / f"ab_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ABTestAnalyzer:
    """Main class for A/B test analysis of product rankings"""
    
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
        
        logger.info("ABTestAnalyzer initialized")
    
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
        """Add or replace opt_seg parameter in URL"""
        parsed = urlparse(base_url)
        query_params = parse_qs(parsed.query)
        
        # Extract parameter key and value
        if '?' in param:
            param = param.replace('?', '')
        key, value = param.split('=')
        
        # Update or add the parameter
        query_params[key] = [value]
        
        # Rebuild the URL
        new_query = urlencode(query_params, doseq=True)
        new_parsed = parsed._replace(query=new_query)
        
        return urlunparse(new_parsed)
    
    def capture_screenshot(self, url, variant_name, url_index):
        """Capture screenshot of a URL and extract page data"""
        try:
            logger.info(f"Capturing {variant_name} for URL {url_index}: {url}")
            
            self.driver.get(url)
            time.sleep(config.SELENIUM_WAIT_TIME)
            
            # Wait for content to load
            WebDriverWait(self.driver, config.SELENIUM_TIMEOUT).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Extract page data
            page_data = self.extract_page_data()
            
            # Generate filename
            url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
            filename = f"url_{url_index:03d}_{variant_name}_{url_hash}.png"
            screenshot_path = config.SCREENSHOTS_DIR / filename
            
            # Take screenshot
            self.driver.save_screenshot(str(screenshot_path))
            logger.info(f"Screenshot saved: {filename}")
            
            return {
                'screenshot_path': str(screenshot_path),
                'filename': filename,
                'url': url,
                'variant': variant_name,
                **page_data
            }
            
        except TimeoutException:
            logger.error(f"Timeout loading {url}")
            return None
        except Exception as e:
            logger.error(f"Error capturing screenshot for {url}: {e}")
            return None
    
    def extract_page_data(self):
        """Extract relevant data from the current page"""
        try:
            # Get page source for parsing
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Extract H1 title (search query)
            h1_element = soup.find('h1')
            h1_text = h1_element.get_text(strip=True) if h1_element else "No H1 found"
            
            # Extract product titles (first 10)
            product_titles = []
            
            # Try different possible product selectors
            product_selectors = [
                'article h2',
                'article h3',
                '.product-title',
                '.product-name',
                '[data-test*="product"] h2',
                '[data-test*="product"] h3'
            ]
            
            for selector in product_selectors:
                products = soup.select(selector)
                if products:
                    product_titles = [p.get_text(strip=True) for p in products[:10]]
                    break
            
            # If no products found with specific selectors, try generic approach
            if not product_titles:
                all_h2_h3 = soup.find_all(['h2', 'h3'])
                product_titles = [h.get_text(strip=True) for h in all_h2_h3[:10] if len(h.get_text(strip=True)) > 10]
            
            return {
                'h1_title': h1_text,
                'product_count': len(product_titles),
                'product_titles': product_titles[:10]  # First 10 products
            }
            
        except Exception as e:
            logger.error(f"Error extracting page data: {e}")
            return {
                'h1_title': "Error extracting",
                'product_count': 0,
                'product_titles': []
            }
    
    def analyze_with_gpt(self, variant_a_data, variant_b_data):
        """Use GPT-5-mini to analyze which ranking is better"""
        
        # Prepare images for GPT
        def encode_image(image_path):
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        
        # Create the analysis prompt with enriched product data
        def format_products(product_data):
            """Format product data with enriched information"""
            products_str = ""
            for i, product in enumerate(product_data[:5], 1):
                # For now we only have titles, but structure it for future enrichment
                products_str += f'{i}. {{ "title": "{product}", "price": "N/A", "rating": "N/A", "reviews": "N/A", "tags": [] }}\n'
            return products_str.strip()
        
        prompt = f"""
        You are an expert in e-commerce product ranking algorithms. Evaluate which algorithm produces BETTER PRODUCT RANKINGS based on the data below.
        
        Search Query: {variant_a_data.get('h1_title', 'Unknown')}
        
        Version A (opt_seg=5) Top Products:
        {format_products(variant_a_data.get('product_titles', []))}
        
        Version B (opt_seg=6) Top Products:
        {format_products(variant_b_data.get('product_titles', []))}
        
        Return JSON:
        {{
            "winner": "A", "B", or "Tie",
            "confidence": <number 0.5-1.0>,
            "winner_summary": "Max 6 words explaining why it wins.",
            "score_a": <number 1-10>,
            "score_b": <number 1-10>,
            "reasoning": "1-2 sentences max explaining the evaluation.",
            "key_differences": "1 sentence on the main ranking difference, focusing on product placement."
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
                "model": config.OPENAI_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a senior e-commerce ranking expert. Your sole focus is to evaluate ranking performance based on the provided data. You must analyze query relevance, the placement of high-value products (like bestsellers or items with high ratings), and overall product matching. Prioritize relevance in the top 3 positions. Be EXTREMELY CONCISE and adhere strictly to the JSON output format."
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_a_base64}",
                                    "detail": "low"  # Use low detail for cost efficiency
                                }
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_b_base64}",
                                    "detail": "low"
                                }
                            }
                        ]
                    }
                ],
                "response_format": {"type": "json_object"},
                "max_tokens": 500,
                "temperature": 0.3
            }
            
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                analysis = json.loads(result['choices'][0]['message']['content'])
                logger.info(f"GPT analysis completed: Winner={analysis.get('winner')}")
                return analysis
            else:
                logger.error(f"GPT API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error in GPT analysis: {e}")
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
        
        # Analyze with GPT
        analysis = self.analyze_with_gpt(variant_a_data, variant_b_data)
        
        if not analysis:
            logger.warning(f"GPT analysis failed for URL {url_index}")
            analysis = {
                "winner": "unknown",
                "confidence": 0.5,
                "score_a": 0,
                "score_b": 0,
                "reasoning": "Analysis failed",
                "key_differences": "Unable to analyze"
            }
        
        # Compile results
        result = {
            "url_index": url_index,
            "original_url": url,
            "visits": visits,
            "variant_a": {
                "url": url_a,
                "screenshot": variant_a_data['filename'],
                "h1_title": variant_a_data.get('h1_title'),
                "product_count": variant_a_data.get('product_count'),
                "score": analysis.get('score_a', 0)
            },
            "variant_b": {
                "url": url_b,
                "screenshot": variant_b_data['filename'],
                "h1_title": variant_b_data.get('h1_title'),
                "product_count": variant_b_data.get('product_count'),
                "score": analysis.get('score_b', 0)
            },
            "analysis": {
                "winner": analysis.get('winner'),
                "confidence": analysis.get('confidence', 0.5),
                "winner_summary": analysis.get('winner_summary', 'Better ranking quality'),
                "reasoning": analysis.get('reasoning'),
                "key_differences": analysis.get('key_differences')
            },
            "timestamp": datetime.now().isoformat()
        }
        
        # Save individual result
        result_file = config.RESULTS_DIR / f"result_{url_index:03d}.json"
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        return result
    
    def run_analysis(self, limit=None, start_from=None):
        """Run the complete A/B test analysis
        
        Args:
            limit: Maximum number of URLs to process
            start_from: URL index to start from (1-based)
        """
        
        logger.info("Starting A/B test analysis")
        
        # Load existing results if resuming
        if start_from and start_from > 1:
            results_file = config.RESULTS_DIR / "all_results.json"
            if results_file.exists():
                with open(results_file, 'r') as f:
                    self.results = json.load(f)
                logger.info(f"Loaded {len(self.results)} existing results")
        
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
        
        # Limit processing if requested
        if limit:
            df = df.head(limit)
            logger.info(f"Processing limited to {limit} URLs")
        
        # Setup WebDriver
        self.setup_driver()
        
        try:
            # Process each URL
            total_urls = len(pd.read_excel(config.INPUT_FILE))  # Get total count
            for index, row in df.iterrows():
                url = row['url']
                visits = row.get('visits', 0)
                url_index = index + 1  # 1-based index
                
                logger.info(f"Processing URL {url_index}/{total_urls}")
                
                result = self.process_url(url, url_index, visits)
                if result:
                    self.results.append(result)
                
                # Save intermediate results
                if (index + 1) % 5 == 0:
                    self.save_results()
                    logger.info(f"Intermediate save: {index + 1} URLs processed")
            
            # Save final results
            self.save_results()
            logger.info(f"Analysis complete: {len(self.results)} URLs processed")
            
            # Calculate overall statistics
            self.calculate_statistics()
            
        finally:
            self.close_driver()
        
        return self.results
    
    def save_results(self):
        """Save all results to a JSON file"""
        results_file = config.RESULTS_DIR / "all_results.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        logger.info(f"Results saved to {results_file}")
    
    def calculate_statistics(self):
        """Calculate overall statistics for the A/B test"""
        
        if not self.results:
            logger.warning("No results to calculate statistics")
            return
        
        wins_a = sum(1 for r in self.results if r['analysis']['winner'] == 'A')
        wins_b = sum(1 for r in self.results if r['analysis']['winner'] == 'B')
        ties = sum(1 for r in self.results if r['analysis']['winner'] == 'Tie')
        unknown = len(self.results) - wins_a - wins_b - ties
        
        avg_score_a = sum(r['variant_a']['score'] for r in self.results) / len(self.results)
        avg_score_b = sum(r['variant_b']['score'] for r in self.results) / len(self.results)
        
        # Weight by visits
        weighted_score_a = sum(r['variant_a']['score'] * r.get('visits', 1) for r in self.results)
        weighted_score_b = sum(r['variant_b']['score'] * r.get('visits', 1) for r in self.results)
        total_visits = sum(r.get('visits', 1) for r in self.results)
        
        # Calculate average confidence
        avg_confidence = sum(r['analysis'].get('confidence', 0.5) for r in self.results) / len(self.results)
        
        stats = {
            "total_urls": len(self.results),
            "variant_a_wins": wins_a,
            "variant_b_wins": wins_b,
            "ties": ties,
            "unknown": unknown,
            "average_score_a": round(avg_score_a, 2),
            "average_score_b": round(avg_score_b, 2),
            "average_confidence": round(avg_confidence, 2),
            "weighted_score_a": round(weighted_score_a / total_visits, 2),
            "weighted_score_b": round(weighted_score_b / total_visits, 2),
            "overall_winner": "A (opt_seg=5)" if wins_a > wins_b else "B (opt_seg=6)" if wins_b > wins_a else "Tie",
            "win_percentage_a": round(wins_a / len(self.results) * 100, 1),
            "win_percentage_b": round(wins_b / len(self.results) * 100, 1),
            "tie_percentage": round(ties / len(self.results) * 100, 1)
        }
        
        # Save statistics
        stats_file = config.RESULTS_DIR / "statistics.json"
        with open(stats_file, 'w') as f:
            json.dump(stats, f, indent=2)
        
        logger.info(f"Statistics calculated: {stats}")
        
        return stats


def main():
    """Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run A/B test analysis on product rankings')
    parser.add_argument('--limit', type=int, help='Limit number of URLs to process')
    args = parser.parse_args()
    
    analyzer = ABTestAnalyzer()
    
    try:
        results = analyzer.run_analysis(limit=args.limit)
        print(f"\nAnalysis complete! Processed {len(results)} URLs")
        print(f"Results saved in: {config.RESULTS_DIR}")
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise


if __name__ == "__main__":
    main()