#!/usr/bin/env python3
"""
Script to fetch product data using the API client and then analyze the products
and generate a PDF report.
"""

import os
import argparse
import json
from pathlib import Path
import datetime

import api_client
import product_analyzer
import config

def main():
    """Main function to run the analysis pipeline."""
    parser = argparse.ArgumentParser(description='Fetch product data, analyze it, and generate a report')
    parser.add_argument('--category', type=str, default=config.DEFAULT_CATEGORY,
                        help=f'Product category (default: {config.DEFAULT_CATEGORY})')
    parser.add_argument('--limit', type=int, default=config.DEFAULT_LIMIT,
                        help=f'Number of products to fetch (default: {config.DEFAULT_LIMIT})')
    parser.add_argument('--output-dir', type=str, default='analysis_results',
                        help='Directory to store analysis results (default: analysis_results)')
    parser.add_argument('--data-dir', type=str, default=config.DEFAULT_OUTPUT_DIR,
                        help=f'Directory to store API data (default: {config.DEFAULT_OUTPUT_DIR})')
    parser.add_argument('--skip-fetch', action='store_true',
                        help='Skip fetching data and use existing latest_result.json')
    
    args = parser.parse_args()
    
    # Create output directories
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    data_dir = Path(args.data_dir)
    data_dir.mkdir(exist_ok=True)
    
    # Step 1: Fetch product data (or use existing data)
    if args.skip_fetch:
        print("Skipping data fetch, using existing data...")
        latest_result_file = data_dir / "latest_result.json"
        
        if not latest_result_file.exists():
            print(f"Error: {latest_result_file} not found. Run without --skip-fetch first.")
            return 1
        
        try:
            with open(latest_result_file, 'r') as f:
                products_data = json.load(f)
            print(f"Loaded {len(products_data)} products from {latest_result_file}")
        except Exception as e:
            print(f"Error loading product data: {str(e)}")
            return 1
    else:
        print(f"Fetching product data for category: {args.category}, limit: {args.limit}")
        fetch_info, products_data = api_client.fetch_and_process_data(args.category, args.limit, data_dir)
        
        if "error" in fetch_info:
            print(f"Error fetching data: {fetch_info['error']}")
            return 1
        
        print(f"Successfully fetched {len(products_data)} products")
    
    # Step 2: Analyze products and generate report
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    analysis_dir = output_dir / f"analysis_{timestamp}"
    
    print(f"\nStarting product analysis and report generation...")
    print(f"Analysis results will be saved to: {analysis_dir}")
    
    # Initialize the analyzer
    analyzer = product_analyzer.ProductAnalyzer(analysis_dir)
    
    try:
        # Analyze the products
        print(f"Analyzing {len(products_data)} products...")
        analyzer.analyze_products(products_data)
        
        # Generate the PDF report
        print("Generating PDF report...")
        pdf_path = analyzer.generate_pdf_report()
        
        # Clean up
        analyzer.close()
        
        if pdf_path:
            print(f"\nAnalysis complete!")
            print(f"PDF report saved to: {pdf_path}")
            return 0
        else:
            print("Failed to generate PDF report")
            return 1
    
    except Exception as e:
        print(f"Error during analysis: {str(e)}")
        analyzer.close()
        return 1

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code) 