import os
import time
import json
from pathlib import Path
from urllib.parse import urlparse
import re
from datetime import datetime
import requests
import dotenv

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# Load environment variables from .env file
dotenv.load_dotenv()

class ProductAnalyzer:
    """Class to analyze product pages, take screenshots, and generate reports."""
    
    def __init__(self, output_dir="analysis"):
        """Initialize the analyzer with the given output directory."""
        self.output_dir = Path(output_dir)
        self.screenshots_dir = self.output_dir / "screenshots"
        self.results_dir = self.output_dir / "results"
        
        # Create directories if they don't exist
        self.output_dir.mkdir(exist_ok=True)
        self.screenshots_dir.mkdir(exist_ok=True)
        self.results_dir.mkdir(exist_ok=True)
        
        # Initialize webdriver
        self.driver = None
        
        # Results storage
        self.analysis_results = []
        
        # OpenAI API key
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            print("WARNING: OPENAI_API_KEY not found in environment variables. Size detection will use regex fallback.")
    
    def check_size_in_title_with_gpt(self, title):
        """
        Use GPT-4o mini to determine if a product title contains size information.
        
        Args:
            title: The product title to check
            
        Returns:
            Boolean indicating if the title contains size information
        """
        if not self.openai_api_key:
            # Fallback to regex if API key is not available
            size_pattern = r'\b(maat|mt|size)\s*\d+\b|\b\d{2}(\.5)?\b'
            return bool(re.search(size_pattern, title.lower()))
        
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.openai_api_key}"
            }
            
            payload = {
                "model": "gpt-4o-mini",
                "messages": [
                    {
                        "role": "system", 
                        "content": "You are a product analyzer that determines if a product title contains shoe size information. Respond with only 'true' or 'false'."
                    },
                    {
                        "role": "user", 
                        "content": f"Does this product title contain a shoe size? Title: \"{title}\"\nRespond with only 'true' or 'false'."
                    }
                ],
                "temperature": 0.1,
                "max_tokens": 5
            }
            
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                result = response.json()
                ai_response = result["choices"][0]["message"]["content"].strip().lower()
                return ai_response == "true"
            else:
                print(f"Error calling OpenAI API: {response.status_code} - {response.text}")
                # Fallback to regex
                size_pattern = r'\b(maat|mt|size)\s*\d+\b|\b\d{2}(\.5)?\b'
                return bool(re.search(size_pattern, title.lower()))
                
        except Exception as e:
            print(f"Error using GPT to check title: {str(e)}")
            # Fallback to regex
            size_pattern = r'\b(maat|mt|size)\s*\d+\b|\b\d{2}(\.5)?\b'
            return bool(re.search(size_pattern, title.lower()))
    
    def setup_webdriver(self):
        """Set up the Chrome webdriver with appropriate options."""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        print("Setting up Chrome webdriver...")
        self.driver = webdriver.Chrome(options=chrome_options)
    
    def take_screenshot(self, url, product_id):
        """
        Take a screenshot of the given URL and save it to the screenshots directory.
        
        Args:
            url: The URL to take a screenshot of
            product_id: The product ID to use in the filename
            
        Returns:
            Path to the screenshot file
        """
        if self.driver is None:
            self.setup_webdriver()
        
        # Clean URL for filename
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.replace(".", "_")
        screenshot_filename = f"{product_id}_{domain}.png"
        screenshot_path = self.screenshots_dir / screenshot_filename
        
        try:
            print(f"Taking screenshot of {url}...")
            self.driver.get(url)
            
            # Wait for page to load
            time.sleep(3)
            
            # Scroll down to make sure all elements are loaded
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
            time.sleep(1)
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
            
            # Take screenshot
            self.driver.save_screenshot(str(screenshot_path))
            print(f"Screenshot saved to {screenshot_path}")
            
            return screenshot_path
        
        except Exception as e:
            print(f"Error taking screenshot of {url}: {str(e)}")
            return None
    
    def count_shop_sizes(self, soup):
        """
        Count the number of available sizes for each shop.
        
        Args:
            soup: BeautifulSoup object representing the page
            
        Returns:
            Dictionary with shop names as keys and size counts as values,
            and a boolean indicating if any shop has 5 or more sizes
        """
        shop_size_counts = {}
        has_shop_with_many_sizes = False
        
        # Find all shop comparison sections
        comparisons = soup.find_all('div', class_='comparison--Ws_f6')
        
        for comparison in comparisons:
            shop_name_div = comparison.find('div', class_='comparison__shopname--ellipsis--t4Q5X')
            if not shop_name_div:
                continue
                
            shop_name = shop_name_div.get_text(strip=True)
            
            # Find size badges within this shop section
            size_section = comparison.find('div', class_='fashionSize--BhXK5')
            if not size_section:
                continue
                
            size_badges = size_section.find_all('div', class_='fashionSizeBadge--WkUdh')
            size_count = len(size_badges)
            
            shop_size_counts[shop_name] = size_count
            
            if size_count >= 5:
                has_shop_with_many_sizes = True
        
        return shop_size_counts, has_shop_with_many_sizes
    
    def analyze_product_page(self, url, product_id):
        """
        Analyze a product page for the requested information.
        
        Args:
            url: The product URL to analyze
            product_id: The ID of the product
            
        Returns:
            Dictionary with analysis results
        """
        if self.driver is None:
            self.setup_webdriver()
        
        result = {
            "product_id": product_id,
            "url": url,
            "screenshot_path": None,
            "title": None,
            "has_multiple_images": False,
            "has_size_in_title": False,
            "has_reviews": False,
            "shop_size_counts": {},
            "has_shop_with_many_sizes": False,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        try:
            # Take screenshot
            screenshot_path = self.take_screenshot(url, product_id)
            result["screenshot_path"] = str(screenshot_path) if screenshot_path else None
            
            # Get page source for analysis
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Extract title (h1)
            h1_tag = soup.find('h1')
            if h1_tag:
                title = h1_tag.get_text(strip=True)
                result["title"] = title
                
                # Check if title contains size information using GPT-4o mini
                result["has_size_in_title"] = self.check_size_in_title_with_gpt(title)
            
            # Check for multiple images
            thumb_images = soup.find_all('img', class_='thumb__image--rkNhS')
            result["has_multiple_images"] = len(thumb_images) > 1
            
            # Check for reviews
            review_stars = soup.find('span', class_='reviewStars--cqhaF')
            result["has_reviews"] = review_stars is not None
            
            # Count available sizes from shops
            shop_size_counts, has_shop_with_many_sizes = self.count_shop_sizes(soup)
            result["shop_size_counts"] = shop_size_counts
            result["has_shop_with_many_sizes"] = has_shop_with_many_sizes
            
            print(f"Analyzed {url}")
            print(f"  Title: {result['title']}")
            print(f"  Multiple images: {result['has_multiple_images']}")
            print(f"  Size in title: {result['has_size_in_title']}")
            print(f"  Has reviews: {result['has_reviews']}")
            print(f"  Shop size counts: {result['shop_size_counts']}")
            print(f"  Has shop with 5+ sizes: {result['has_shop_with_many_sizes']}")
            
            # Save individual result
            result_file = self.results_dir / f"{product_id}_analysis.json"
            with open(result_file, 'w') as f:
                json.dump(result, f, indent=2)
            
            return result
        
        except Exception as e:
            print(f"Error analyzing {url}: {str(e)}")
            result["error"] = str(e)
            return result
    
    def analyze_products(self, products_data):
        """
        Analyze a list of products.
        
        Args:
            products_data: List of dictionaries with product information
                           Each should have at least 'pim3puntnull' and 'product_url' keys
        
        Returns:
            List of analysis results
        """
        try:
            self.analysis_results = []
            
            for i, product in enumerate(products_data):
                product_id = product.get('pim3puntnull', f"unknown_{i}")
                product_url = product.get('product_url')
                
                if not product_url:
                    print(f"Skipping product {product_id} as it has no URL")
                    continue
                
                print(f"Analyzing product {i+1}/{len(products_data)}: {product_id}")
                result = self.analyze_product_page(product_url, product_id)
                self.analysis_results.append(result)
            
            # Save all results to a single file
            all_results_file = self.output_dir / "all_analysis_results.json"
            with open(all_results_file, 'w') as f:
                json.dump(self.analysis_results, f, indent=2)
            
            return self.analysis_results
        
        except Exception as e:
            print(f"Error during product analysis: {str(e)}")
            return self.analysis_results
    
    def generate_pdf_report(self, output_file=None):
        """
        Generate a PDF report of the analysis results.
        
        Args:
            output_file: File path for the PDF output. If None, uses a default name.
            
        Returns:
            Path to the generated PDF file
        """
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = self.output_dir / f"product_analysis_report_{timestamp}.pdf"
        
        if not self.analysis_results:
            print("No analysis results to generate a report from.")
            return None
        
        try:
            # Create document
            doc = SimpleDocTemplate(str(output_file), pagesize=A4)
            styles = getSampleStyleSheet()
            
            # Create custom styles
            title_style = ParagraphStyle(
                'ReportTitle',
                parent=styles['Heading1'],
                fontSize=24,
                textColor=colors.darkblue,
                spaceAfter=12,
                alignment=1  # Center alignment
            )
            
            heading2_style = ParagraphStyle(
                'Heading2',
                parent=styles['Heading2'],
                fontSize=18,
                textColor=colors.darkblue,
                spaceBefore=12,
                spaceAfter=6
            )
            
            heading3_style = ParagraphStyle(
                'Heading3',
                parent=styles['Heading3'],
                fontSize=14,
                textColor=colors.darkblue,
                spaceBefore=10,
                spaceAfter=4
            )
            
            url_style = ParagraphStyle(
                'URLStyle',
                parent=styles['Normal'],
                textColor=colors.blue,
                fontSize=10
            )
            
            # Content elements
            elements = []
            
            # Title
            elements.append(Paragraph("Product Analysis Report", title_style))
            elements.append(Spacer(1, 20))
            
            # Summary section
            elements.append(Paragraph("Summary", heading2_style))
            elements.append(Spacer(1, 10))
            
            # Calculate summary statistics
            total_products = len(self.analysis_results)
            products_with_multiple_images = sum(1 for r in self.analysis_results if r.get('has_multiple_images', False))
            products_with_size_in_title = sum(1 for r in self.analysis_results if r.get('has_size_in_title', False))
            products_with_reviews = sum(1 for r in self.analysis_results if r.get('has_reviews', False))
            products_with_many_sizes = sum(1 for r in self.analysis_results if r.get('has_shop_with_many_sizes', False))
            
            # Create summary table
            summary_data = [
                ["Metric", "Count", "Percentage"],
                ["Total Products", total_products, "100%"],
                ["Products with Multiple Images", products_with_multiple_images, f"{products_with_multiple_images/total_products*100:.1f}%"],
                ["Products with Size in Title", products_with_size_in_title, f"{products_with_size_in_title/total_products*100:.1f}%"],
                ["Products with Reviews", products_with_reviews, f"{products_with_reviews/total_products*100:.1f}%"],
                ["Products with ≥5 Sizes Available", products_with_many_sizes, f"{products_with_many_sizes/total_products*100:.1f}%"]
            ]
            
            summary_table = Table(summary_data, colWidths=[250, 100, 100])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.lightgrey]),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('PADDING', (0, 0), (-1, -1), 6),
            ]))
            
            elements.append(summary_table)
            elements.append(Spacer(1, 30))
            
            # Individual product sections
            elements.append(Paragraph("Product Details", heading2_style))
            elements.append(Spacer(1, 15))
            
            for result in self.analysis_results:
                # Product title
                product_id = result.get('product_id', 'Unknown')
                title = result.get('title', f'Product {product_id}')
                url = result.get('url', '')
                
                elements.append(Paragraph(title, heading3_style))
                
                # Add URL below the title and make it clickable
                if url:
                    url_text = f'<a href="{url}">{url}</a>'
                    elements.append(Paragraph(url_text, url_style))
                
                elements.append(Spacer(1, 10))
                
                # Create a table for product details
                screenshot_path = result.get('screenshot_path')
                has_shop_with_many_sizes = result.get('has_shop_with_many_sizes', False)
                
                # Check if screenshot exists
                if screenshot_path and os.path.exists(screenshot_path):
                    # Resize image to fit in the document
                    img = Image(screenshot_path, width=250, height=160)
                    
                    # Format the analysis text with better styling
                    analysis_text = f"""
                    <b>Multiple Images:</b> {'Yes' if result.get('has_multiple_images') else 'No'}<br/>
                    <b>Size in Title:</b> {'Yes' if result.get('has_size_in_title') else 'No'}<br/>
                    <b>Has Reviews:</b> {'Yes' if result.get('has_reviews') else 'No'}<br/>
                    <b>Min 1 offer met >5 maten:</b> {'Yes' if has_shop_with_many_sizes else 'No'}<br/>
                    """
                    
                    # Add shop size counts if available
                    shop_counts = result.get('shop_size_counts', {})
                    if shop_counts:
                        analysis_text += "<br/><b>Shop Size Counts:</b><br/>"
                        for shop, count in shop_counts.items():
                            analysis_text += f"• {shop}: {count} sizes<br/>"
                    
                    details_data = [
                        ["Screenshot", "Analysis"],
                        [img, Paragraph(analysis_text, styles['Normal'])]
                    ]
                else:
                    # Format the analysis text with better styling
                    analysis_text = f"""
                    <b>Multiple Images:</b> {'Yes' if result.get('has_multiple_images') else 'No'}<br/>
                    <b>Size in Title:</b> {'Yes' if result.get('has_size_in_title') else 'No'}<br/>
                    <b>Has Reviews:</b> {'Yes' if result.get('has_reviews') else 'No'}<br/>
                    <b>Min 1 offer met >5 maten:</b> {'Yes' if has_shop_with_many_sizes else 'No'}<br/>
                    """
                    
                    # Add shop size counts if available
                    shop_counts = result.get('shop_size_counts', {})
                    if shop_counts:
                        analysis_text += "<br/><b>Shop Size Counts:</b><br/>"
                        for shop, count in shop_counts.items():
                            analysis_text += f"• {shop}: {count} sizes<br/>"
                    
                    details_data = [
                        ["Screenshot", "Analysis"],
                        ["Not available", Paragraph(analysis_text, styles['Normal'])]
                    ]
                
                details_table = Table(details_data, colWidths=[300, 200])
