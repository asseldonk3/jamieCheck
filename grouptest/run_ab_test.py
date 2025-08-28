"""
Main script to run the complete A/B test analysis and generate report
"""

import sys
import logging
from pathlib import Path
from datetime import datetime
import json

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from ab_test_analyzer import ABTestAnalyzer
from report_generator import ABTestReportGenerator
import config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_complete_analysis(limit=None, skip_analysis=False, start_from=None):
    """
    Run the complete A/B test analysis pipeline
    
    Args:
        limit: Limit number of URLs to process (None for all)
        skip_analysis: Skip the analysis phase and just generate report from existing results
        start_from: URL index to start from (1-based)
    """
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Step 1: Run analysis (unless skipped)
    if not skip_analysis:
        logger.info("=" * 60)
        logger.info("Starting A/B Test Analysis")
        logger.info(f"Processing limit: {limit if limit else 'All URLs'}")
        logger.info("=" * 60)
        
        analyzer = ABTestAnalyzer()
        
        try:
            results = analyzer.run_analysis(limit=limit, start_from=start_from)
            logger.info(f"Analysis complete: {len(results)} URLs processed")
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            return False
    else:
        logger.info("Skipping analysis phase, using existing results")
    
    # Step 2: Generate PDF report
    logger.info("=" * 60)
    logger.info("Generating PDF Report")
    logger.info("=" * 60)
    
    results_file = config.RESULTS_DIR / "all_results.json"
    
    if not results_file.exists():
        logger.error(f"Results file not found: {results_file}")
        return False
    
    try:
        generator = ABTestReportGenerator(results_file)
        output_file = config.BASE_DIR / f"{config.REPORT_FILENAME}_{timestamp}.pdf"
        report_path = generator.generate_report(output_file)
        
        logger.info("=" * 60)
        logger.info("A/B TEST ANALYSIS COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Report generated: {report_path}")
        
        # Load and display summary statistics
        stats_file = config.RESULTS_DIR / "statistics.json"
        if stats_file.exists():
            with open(stats_file, 'r') as f:
                stats = json.load(f)
            
            logger.info("")
            logger.info("SUMMARY STATISTICS:")
            logger.info("-" * 40)
            logger.info(f"Overall Winner: {stats.get('overall_winner')}")
            logger.info(f"Variant A Wins: {stats.get('variant_a_wins')} ({stats.get('win_percentage_a')}%)")
            logger.info(f"Variant B Wins: {stats.get('variant_b_wins')} ({stats.get('win_percentage_b')}%)")
            logger.info(f"Average Score A: {stats.get('average_score_a')}/10")
            logger.info(f"Average Score B: {stats.get('average_score_b')}/10")
            logger.info(f"Traffic-Weighted Score A: {stats.get('weighted_score_a')}/10")
            logger.info(f"Traffic-Weighted Score B: {stats.get('weighted_score_b')}/10")
            logger.info("-" * 40)
        
        return True
        
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        return False


def main():
    """Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Run complete A/B test analysis for product rankings',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_ab_test.py                    # Analyze all URLs
  python run_ab_test.py --limit 10         # Analyze first 10 URLs
  python run_ab_test.py --skip-analysis    # Generate report from existing results
  python run_ab_test.py --start-from 42    # Resume from URL 42
        """
    )
    
    parser.add_argument(
        '--limit', 
        type=int, 
        help='Limit number of URLs to process (useful for testing)'
    )
    
    parser.add_argument(
        '--skip-analysis',
        action='store_true',
        help='Skip analysis and generate report from existing results'
    )
    
    parser.add_argument(
        '--start-from',
        type=int,
        help='Start from specific URL index (1-based) - useful for resuming'
    )
    
    args = parser.parse_args()
    
    # Print banner
    print("\n" + "="*60)
    print(" A/B TEST RANKING ANALYSIS SYSTEM")
    print(" Comparing opt_seg=5 vs opt_seg=6")
    print("="*60 + "\n")
    
    # Run the analysis
    success = run_complete_analysis(
        limit=args.limit,
        skip_analysis=args.skip_analysis,
        start_from=args.start_from
    )
    
    if success:
        print("\n✓ Analysis completed successfully!")
        print(f"Check the report in: {config.BASE_DIR}")
    else:
        print("\n✗ Analysis failed. Check logs for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()