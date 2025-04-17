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
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
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
            "review_count": 0,  # Add review count field
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
            
            # Improved review detection focused on review count
            review_count = 0
            
            # 1. Check for specific review class from the example
            product_reviews = soup.find('span', class_='productReviews__text--By4jj')
            if product_reviews:
                print(f"  Found product reviews element: {product_reviews.get_text()}")
                # Extract the review count from text like "3.3/5 (3 reviews)"
                review_text = product_reviews.get_text()
                # Look for numbers in parentheses which typically indicate review count
                count_match = re.search(r'\(\s*(\d+)\s*(?:review|recensie)', review_text, re.IGNORECASE)
                if count_match:
                    try:
                        review_count = int(count_match.group(1))
                        print(f"  Extracted review count: {review_count}")
                    except ValueError:
                        print(f"  Could not convert review count to integer: {count_match.group(1)}")
            
            # 2. Try other common review count patterns if specific class not found
            if review_count == 0:
                # Look for elements with review classes
                review_elements = soup.find_all(['span', 'div'], class_=lambda c: c and ('review' in c.lower() or 'rating' in c.lower()))
                
                for element in review_elements:
                    element_text = element.get_text()
                    # Check for patterns like "(3)" or "3 reviews"
                    count_match = re.search(r'\(\s*(\d+)\s*\)|\b(\d+)\s*(?:review|recensie)', element_text, re.IGNORECASE)
                    if count_match:
                        try:
                            # Extract matched group, accounting for two possible capture groups
                            matched_count = count_match.group(1) or count_match.group(2)
                            review_count = int(matched_count)
                            print(f"  Found review count in element: {element_text} -> {review_count}")
                            break
                        except (ValueError, IndexError):
                            continue
            
            # 3. If still no count but we have review indicators, set a default count of 1
            if review_count == 0:
                # Check for star rating elements
                star_ratings = soup.find_all(['span', 'div'], class_=lambda c: c and ('star' in c.lower() or 'rating' in c.lower()))
                # Look specifically for orange/yellow stars which usually indicate a review
                if any(star_ratings):
                    review_count = 1
                    print(f"  Found star rating elements, setting default review count to 1")
            
            # Set review results
            result["review_count"] = review_count
            result["has_reviews"] = review_count > 0
            
            print(f"  Final review count: {review_count}")
            print(f"  Has reviews: {result['has_reviews']}")
            
            # Count available sizes from shops
            shop_size_counts, has_shop_with_many_sizes = self.count_shop_sizes(soup)
            result["shop_size_counts"] = shop_size_counts
            result["has_shop_with_many_sizes"] = has_shop_with_many_sizes
            
            print(f"Analyzed {url}")
            print(f"  Title: {result['title']}")
            print(f"  Multiple images: {result['has_multiple_images']}")
            print(f"  Size in title: {result['has_size_in_title']}")
            print(f"  Has reviews: {result['has_reviews']} (Count: {result['review_count']})")
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
            # Create document with custom page size and margins (explicitly set portrait orientation)
            doc = SimpleDocTemplate(
                str(output_file), 
                pagesize=A4,  # A4 is portrait by default: (width=595.2, height=841.8) points
                rightMargin=30,
                leftMargin=30,
                topMargin=30,
                bottomMargin=30
            )
            styles = getSampleStyleSheet()
            
            # Create custom styles with better typography
            title_style = ParagraphStyle(
                'ReportTitle',
                parent=styles['Heading1'],
                fontSize=22,
                textColor=colors.darkblue,
                spaceAfter=16,
                alignment=1,  # Center alignment
                fontName='Helvetica-Bold'
            )
            
            heading2_style = ParagraphStyle(
                'Heading2',
                parent=styles['Heading2'],
                fontSize=18,
                textColor=colors.darkblue,
                spaceBefore=14,
                spaceAfter=10,
                fontName='Helvetica-Bold'
            )
            
            heading3_style = ParagraphStyle(
                'Heading3',
                parent=styles['Heading3'],
                fontSize=16,
                textColor=colors.darkblue,
                spaceBefore=10,
                spaceAfter=6,
                fontName='Helvetica-Bold'
            )
            
            url_style = ParagraphStyle(
                'URLStyle',
                parent=styles['Normal'],
                textColor=colors.blue,
                fontSize=10,
                spaceAfter=15
            )
            
            normal_style = ParagraphStyle(
                'CustomNormal',
                parent=styles['Normal'],
                fontSize=11,
                leading=14
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
            elements.append(Spacer(1, 20))
            
            # Page break after summary
            elements.append(Paragraph("Product Details", heading2_style))
            elements.append(Spacer(1, 5))
            elements.append(Paragraph("Each product is shown on a separate page with analysis results.", normal_style))
            elements.append(Spacer(1, 5))
            elements.append(PageBreak())
            
            # Individual product sections - one per page
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
                
                # Create a table for product details
                screenshot_path = result.get('screenshot_path')
                has_shop_with_many_sizes = result.get('has_shop_with_many_sizes', False)
                
                # Format the analysis text with better styling
                analysis_text = f"""
                <b>Multiple Images:</b> {'Yes' if result.get('has_multiple_images') else 'No'}<br/>
                <b>Size in Title:</b> {'Yes' if result.get('has_size_in_title') else 'No'}<br/>
                <b>Has Reviews:</b> {'Yes' if result.get('has_reviews') else 'No'} {f"({result.get('review_count')} reviews)" if result.get('review_count', 0) > 0 else ""}<br/>
                <b>Min 1 offer met >5 maten:</b> {'Yes' if has_shop_with_many_sizes else 'No'}<br/>
                """
                
                # Add shop size counts if available
                shop_counts = result.get('shop_size_counts', {})
                if shop_counts:
                    analysis_text += "<br/><b>Shop Size Counts:</b><br/>"
                    for shop, count in shop_counts.items():
                        analysis_text += f"• {shop}: {count} sizes<br/>"
                
                # Check if screenshot exists
                if screenshot_path and os.path.exists(screenshot_path):
                    # Larger image size for better visibility
                    img = Image(screenshot_path, width=400, height=250)
                    
                    details_data = [
                        ["Screenshot", "Analysis"],
                        [img, Paragraph(analysis_text, normal_style)]
                    ]
                else:
                    details_data = [
                        ["Screenshot", "Analysis"],
                        ["Not available", Paragraph(analysis_text, normal_style)]
                    ]
                
                # Use more space for the screenshot (70%) and less for the text (30%)
                details_table = Table(details_data, colWidths=[400, 130])
                details_table.setStyle(TableStyle([
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                    ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('PADDING', (0, 0), (-1, -1), 8),
                    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ]))
                
                elements.append(details_table)
                
                # Add a page break after each product (except the last one)
                if result != self.analysis_results[-1]:
                    elements.append(PageBreak())
            
            # Add page numbers
            def add_page_number(canvas, doc):
                page_num = canvas.getPageNumber()
                text = f"Page {page_num}"
                canvas.setFont("Helvetica", 9)
                canvas.setFillColor(colors.grey)
                canvas.drawRightString(doc.pagesize[0] - 30, 30, text)
                
                # Add report title to each page header
                if page_num > 1:  # Skip the first page which already has the title
                    canvas.setFont("Helvetica-Bold", 10)
                    canvas.setFillColor(colors.darkblue)
                    canvas.drawString(30, doc.pagesize[1] - 30, "Product Analysis Report")
            
            # Build the PDF with page numbers
            doc.build(elements, onFirstPage=add_page_number, onLaterPages=add_page_number)
            print(f"PDF report generated at {output_file}")
            return output_file
        
        except Exception as e:
            print(f"Error generating PDF report: {str(e)}")
            return None
    
    def close(self):
        """Close the webdriver and clean up."""
        if self.driver:
            self.driver.quit()
            self.driver = None


def analyze_products_from_file(input_file, output_dir="analysis"):
    """
    Analyze products from a JSON file and generate a report.
    
    Args:
        input_file: Path to the JSON file containing product data
        output_dir: Directory to store analysis output
        
    Returns:
        Path to the generated PDF report
    """
    try:
        # Load product data
        with open(input_file, 'r') as f:
            products_data = json.load(f)
        
        # Initialize analyzer
        analyzer = ProductAnalyzer(output_dir)
        
        # Analyze products
        analyzer.analyze_products(products_data)
        
        # Generate report
        pdf_path = analyzer.generate_pdf_report()
        
        # Clean up
        analyzer.close()
        
        return pdf_path
    
    except Exception as e:
        print(f"Error analyzing products from file: {str(e)}")
        return None


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Analyze product pages and generate a report')
    parser.add_argument('--input', type=str, required=True, help='Input JSON file with product data')
    parser.add_argument('--output-dir', type=str, default='analysis', help='Output directory for analysis results')
    
    args = parser.parse_args()
    
    pdf_path = analyze_products_from_file(args.input, args.output_dir)
    if pdf_path:
        print(f"Analysis complete. PDF report saved to: {pdf_path}")
    else:
        print("Analysis failed. See error messages above for details.") 