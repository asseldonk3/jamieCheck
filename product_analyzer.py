import os
import time
import json
from pathlib import Path
from urllib.parse import urlparse
import re
from datetime import datetime
import requests
import dotenv
import base64
import io

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from reportlab.lib.pagesizes import letter, A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from PIL import Image as PILImage

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
            print("WARNING: OPENAI_API_KEY not found in environment variables. Image analysis will not work.")
    
    def analyze_image_with_gpt4o(self, image_path, prompt):
        """
        Use GPT-4o to analyze a screenshot and detect features.
        
        Args:
            image_path: Path to the screenshot image
            prompt: The prompt to send to GPT-4o
            
        Returns:
            Dictionary with analysis results
        """
        if not self.openai_api_key:
            print("ERROR: OPENAI_API_KEY not found in environment variables.")
            return {"error": "API key not found"}
        
        try:
            # Convert image to base64
            with open(image_path, "rb") as image_file:
                image_data = base64.b64encode(image_file.read()).decode('utf-8')
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.openai_api_key}"
            }
            
            payload = {
                "model": "gpt-5-mini",
                "messages": [
                    {
                        "role": "system", 
                        "content": "You are a precise product page analyzer. You will be shown screenshots of product pages, and you need to identify specific features. Please respond in JSON format with true/false and numerical values only."
                    },
                    {
                        "role": "user", 
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
                        ]
                    }
                ],
                "response_format": {"type": "json_object"}
            }
            
            print("Sending screenshot to GPT-5-mini for analysis...")
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                result = response.json()
                ai_response = json.loads(result["choices"][0]["message"]["content"])
                print(f"GPT-5-mini analysis result: {ai_response}")
                return ai_response
            else:
                print(f"Error calling OpenAI API: {response.status_code} - {response.text}")
                return {"error": f"API error: {response.status_code}"}
                
        except Exception as e:
            print(f"Error using GPT-5-mini to analyze image: {str(e)}")
            return {"error": str(e)}
    
    def check_size_in_title_with_gpt(self, title):
        """
        Use GPT-5-mini to determine if a product title contains size information.
        
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
                "model": "gpt-5-mini",
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
            "review_count": 0,
            "shop_size_counts": {},  # Shop name -> size count
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
                
                # This will be handled by GPT-4o in the image analysis now
                result["has_size_in_title"] = False
            
            # Count available sizes from shops for fallback
            shop_size_counts, has_shop_with_many_sizes = self.count_shop_sizes(soup)
            result["shop_size_counts"] = shop_size_counts
            
            # Set has_shop_with_many_sizes based on the actual counts
            # Check if any shop has 5 or more sizes
            result["has_shop_with_many_sizes"] = any(count >= 5 for count in shop_size_counts.values())
            
            # Check for multiple images
            thumb_images = soup.find_all('img', class_='thumb__image--rkNhS')
            result["has_multiple_images"] = len(thumb_images) > 1
            
            # Use GPT-4o to analyze the screenshot for reviews and sizes
            if screenshot_path and self.openai_api_key:
                prompt = """
                Please analyze this product page screenshot from an e-commerce site and answer the following questions about the product. Focus specifically on:

                1. Product Reviews: Does this product have PRODUCT reviews? 
                   - Look ONLY for star ratings directly under the H1 product title and above the product image
                   - IMPORTANT: Do NOT count shop/store reviews (star ratings next to shop names like "bol.com" or "Daka.nl")
                   - Product reviews typically show as gold/yellow stars followed by a number like "4.5/5 (3 reviews)"
                   - We're only interested in reviews for the product itself, not for the shops selling it

                2. Available Sizes: Are multiple sizes available for this product? Look for size selection options, size charts, or size badges in the shop sections.

                Return your answer as a JSON object with these fields:
                - "has_reviews": true/false - whether the product has product reviews (not shop reviews)
                - "review_count": number - how many product reviews are shown (0 if none)
                - "has_multiple_sizes": true/false - whether multiple sizes are available
                - "has_size_in_title": true/false - whether the product title contains size information
                """
                
                analysis_result = self.analyze_image_with_gpt4o(screenshot_path, prompt)
                
                if not isinstance(analysis_result, dict) or "error" in analysis_result:
                    print(f"Error in GPT-4o analysis, using fallback methods")
                else:
                    # Extract review information
                    result["has_reviews"] = analysis_result.get("has_reviews", False)
                    result["review_count"] = analysis_result.get("review_count", 0)
                    
                    # Extract size information from GPT-4o
                    result["has_size_in_title"] = analysis_result.get("has_size_in_title", False)
                    
                    # NOTE: We don't update has_shop_with_many_sizes here anymore
                    # It's now exclusively determined by the shop size counts
            else:
                print("Skipping GPT-4o analysis due to missing screenshot or API key")
            
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
            # Create document with custom page size and margins (explicitly set landscape orientation)
            doc = SimpleDocTemplate(
                str(output_file), 
                pagesize=landscape(A4),  # Switch to landscape orientation
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
            
            # Create summary table - adjusted width for landscape
            summary_data = [
                ["Metric", "Count", "Percentage"],
                ["Total Products", total_products, "100%"],
                ["Products with Multiple Images", products_with_multiple_images, f"{products_with_multiple_images/total_products*100:.1f}%"],
                ["Products with Size in Title", products_with_size_in_title, f"{products_with_size_in_title/total_products*100:.1f}%"],
                ["Products with Reviews", products_with_reviews, f"{products_with_reviews/total_products*100:.1f}%"],
                ["Products with ≥5 Sizes Available", products_with_many_sizes, f"{products_with_many_sizes/total_products*100:.1f}%"]
            ]
            
            # Wider table for landscape mode
            summary_table = Table(summary_data, colWidths=[300, 130, 130])
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
                
                # Get shop URLs from the original data
                original_data = {}
                from pathlib import Path
                import json
                
                try:
                    data_file = Path("data/latest_result.json")
                    if data_file.exists():
                        with open(data_file, 'r') as f:
                            all_products = json.load(f)
                            
                        # Find this product in the data
                        for product in all_products:
                            if product.get("pim3puntnull") == product_id:
                                original_data = product
                                break
                except Exception as e:
                    print(f"Error loading original product data: {str(e)}")
                
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
                
                # Add shop size counts if available with clickable links
                shop_data = result.get('shop_size_counts', {})
                if shop_data:
                    analysis_text += "<br/><b>Shop Size Counts:</b><br/>"
                    
                    # Get shop names in a consistent order
                    shop_names = list(shop_data.keys())
                    
                    for i, shop_name in enumerate(shop_names):
                        size_count = shop_data[shop_name]
                        # Use the corresponding URL from the original data
                        shop_url = original_data.get(f"url{i+1}", "#")
                        
                        # Clearly format the shop name, properly escaping HTML entities
                        safe_shop_name = shop_name.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                        
                        if shop_url and shop_url != "#":
                            # Format with proper HTML link styling for better visibility in PDF
                            analysis_text += f'• <a href="{shop_url}" color="#0000FF"><u>{safe_shop_name}</u></a>: {size_count} sizes<br/>'
                        else:
                            analysis_text += f"• {safe_shop_name}: {size_count} sizes<br/>"
                
                # Check if screenshot exists
                if screenshot_path and os.path.exists(screenshot_path):
                    # Adjust image size to ensure it fits on one page with analysis
                    img = Image(screenshot_path, width=700, height=280)
                    
                    # Create a table with the screenshot and analysis
                    # Use a simpler structure to ensure everything stays on one page
                    analysis_paragraph = Paragraph(analysis_text, normal_style)
                    
                    # Create a KeepTogether flowable to ensure all content stays on one page
                    from reportlab.platypus import KeepTogether
                    
                    # Create a single content block with the screenshot, header, and analysis
                    content_elements = []
                    content_elements.append(Paragraph("Screenshot", heading3_style))
                    content_elements.append(img)
                    content_elements.append(Spacer(1, 10))
                    content_elements.append(Paragraph("Analysis", heading3_style))
                    content_elements.append(analysis_paragraph)
                    
                    # Wrap everything in a KeepTogether to ensure it stays on one page
                    product_content = KeepTogether(content_elements)
                    elements.append(product_content)
                else:
                    # Create a KeepTogether flowable for products without screenshots
                    from reportlab.platypus import KeepTogether
                    
                    content_elements = []
                    content_elements.append(Paragraph("Screenshot", heading3_style))
                    content_elements.append(Paragraph("Not available", normal_style))
                    content_elements.append(Spacer(1, 10))
                    content_elements.append(Paragraph("Analysis", heading3_style))
                    content_elements.append(Paragraph(analysis_text, normal_style))
                    
                    product_content = KeepTogether(content_elements)
                    elements.append(product_content)
                
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