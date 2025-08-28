#!/usr/bin/env python3
"""
Run the enhanced A/B test analysis with duplicate detection using GPT-5-mini
This analyzes how opt_seg=5 groups offers from same webshop vs opt_seg=6 that doesn't
"""

import sys
import logging
from pathlib import Path
from datetime import datetime
import json

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from ab_test_analyzer_enhanced import EnhancedABTestAnalyzer
import config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Run the enhanced analysis with duplicate detection"""
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    logger.info("=" * 80)
    logger.info("ENHANCED A/B TEST ANALYSIS - DUPLICATE DETECTION")
    logger.info("=" * 80)
    logger.info("Analyzing opt_seg=5 (groups same-shop offers) vs opt_seg=6 (shows all)")
    logger.info(f"Using model: {config.OPENAI_MODEL}")
    logger.info("=" * 80)
    
    # Create analyzer
    analyzer = EnhancedABTestAnalyzer()
    
    # Parse arguments
    import argparse
    parser = argparse.ArgumentParser(description='Run enhanced A/B test analysis')
    parser.add_argument('--limit', type=int, default=10,
                       help='Number of URLs to analyze (default: 10)')
    parser.add_argument('--start-from', type=int, default=None,
                       help='URL index to start from (1-based)')
    parser.add_argument('--test', action='store_true',
                       help='Test mode - analyze first 5 URLs only')
    args = parser.parse_args()
    
    if args.test:
        limit = 5
        logger.info("TEST MODE: Analyzing first 5 URLs only")
    else:
        limit = args.limit
    
    try:
        # Run the analysis
        results = analyzer.run_analysis(limit=limit, start_from=args.start_from)
        
        # Load and display enhanced statistics
        stats_file = config.RESULTS_DIR / "enhanced_statistics.json"
        if stats_file.exists():
            with open(stats_file, 'r') as f:
                stats = json.load(f)
            
            logger.info("")
            logger.info("=" * 80)
            logger.info("DUPLICATE DETECTION RESULTS")
            logger.info("=" * 80)
            logger.info("")
            logger.info("SUMMARY:")
            logger.info("-" * 40)
            logger.info(f"URLs Analyzed: {stats.get('total_urls')}")
            logger.info("")
            logger.info("WINNER BREAKDOWN:")
            logger.info(f"  Variant A (opt_seg=5) Wins: {stats.get('variant_a_wins')} ({stats.get('win_percentage_a', 0):.1f}%)")
            logger.info(f"  Variant B (opt_seg=6) Wins: {stats.get('variant_b_wins')} ({stats.get('win_percentage_b', 0):.1f}%)")
            logger.info(f"  Ties: {stats.get('ties')}")
            logger.info("")
            logger.info("DUPLICATE ANALYSIS:")
            logger.info(f"  Average Duplicates in A (grouped): {stats.get('avg_duplicates_a', 0):.2f}")
            logger.info(f"  Average Duplicates in B (ungrouped): {stats.get('avg_duplicates_b', 0):.2f}")
            logger.info(f"  Duplicate Reduction: {stats.get('duplicate_reduction_percentage', 0):.1f}%")
            logger.info("")
            logger.info("UNIQUE PRODUCTS:")
            logger.info(f"  Average Unique Products in A: {stats.get('avg_unique_products_a', 0):.2f}")
            logger.info(f"  Average Unique Products in B: {stats.get('avg_unique_products_b', 0):.2f}")
            logger.info("")
            logger.info("CONCLUSION:")
            if stats.get('avg_duplicates_a', 0) < stats.get('avg_duplicates_b', 0):
                logger.info("  ✓ opt_seg=5 (A) successfully reduces duplicates by grouping same-shop offers")
            else:
                logger.info("  ✗ No significant duplicate reduction observed")
            logger.info("=" * 80)
        
        logger.info("")
        logger.info(f"Enhanced results saved to: {config.RESULTS_DIR / 'enhanced_results.json'}")
        logger.info("Analysis complete!")
        return True
        
    except Exception as e:
        logger.error(f"Enhanced analysis failed: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)