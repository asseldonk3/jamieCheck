#!/usr/bin/env python3
"""
Run a representative sample analysis of 20 URLs
"""

import sys
import logging
import json
from pathlib import Path
from datetime import datetime

sys.path.append(str(Path(__file__).parent.parent))

from ab_test_analyzer_enhanced import EnhancedABTestAnalyzer
from report_generator import ABTestReportGenerator
import config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Run analysis on 20 URLs"""
    
    logger.info("=" * 80)
    logger.info("RUNNING SAMPLE ENHANCED ANALYSIS (20 URLs)")
    logger.info("=" * 80)
    
    # Get current progress
    results_file = config.RESULTS_DIR / "enhanced_results.json"
    if results_file.exists():
        with open(results_file, 'r') as f:
            current_results = json.load(f)
        start_from = len(current_results) + 1
    else:
        start_from = 1
    
    logger.info(f"Starting from URL {start_from}")
    
    # Run analysis
    analyzer = EnhancedABTestAnalyzer()
    
    # Calculate how many more we need to reach 20
    target = 20
    if start_from <= target:
        to_process = target - start_from + 1
        logger.info(f"Processing {to_process} URLs to reach target of {target}")
        
        results = analyzer.run_analysis(
            limit=to_process,
            start_from=start_from
        )
        
        logger.info(f"Sample analysis complete: {len(results)} new URLs processed")
    else:
        logger.info(f"Already have {start_from-1} URLs, target of {target} reached")
    
    # Generate report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    logger.info("Generating PDF report...")
    generator = ABTestReportGenerator(results_file)
    output_file = config.BASE_DIR / f"sample_ab_test_report_{timestamp}.pdf"
    report_path = generator.generate_report(output_file)
    
    logger.info(f"Report generated: {report_path}")
    
    # Analyze results
    with open(results_file, 'r') as f:
        all_results = json.load(f)
    
    logger.info("\n" + "=" * 80)
    logger.info("SAMPLE ANALYSIS SUMMARY")
    logger.info("=" * 80)
    
    total = len(all_results)
    wins_a = sum(1 for r in all_results if r['analysis']['winner'] == 'A')
    wins_b = sum(1 for r in all_results if r['analysis']['winner'] == 'B')
    ties = sum(1 for r in all_results if r['analysis']['winner'] == 'Tie')
    
    logger.info(f"Total URLs analyzed: {total}")
    logger.info(f"Variant A wins: {wins_a} ({wins_a/total*100:.1f}%)")
    logger.info(f"Variant B wins: {wins_b} ({wins_b/total*100:.1f}%)")
    logger.info(f"Ties: {ties} ({ties/total*100:.1f}%)")
    
    # Duplicate analysis
    duplicates_a = [r['variant_a']['duplicates'] for r in all_results if r['variant_a']['duplicates'] >= 0]
    duplicates_b = [r['variant_b']['duplicates'] for r in all_results if r['variant_b']['duplicates'] >= 0]
    
    if duplicates_a and duplicates_b:
        avg_dup_a = sum(duplicates_a) / len(duplicates_a)
        avg_dup_b = sum(duplicates_b) / len(duplicates_b)
        
        logger.info(f"\nAverage duplicates in A: {avg_dup_a:.2f}")
        logger.info(f"Average duplicates in B: {avg_dup_b:.2f}")
        
        if avg_dup_a < avg_dup_b:
            logger.info(f"✓ opt_seg=5 reduces duplicates by {(avg_dup_b-avg_dup_a)/avg_dup_b*100:.1f}%")
        elif avg_dup_b < avg_dup_a:
            logger.info(f"✗ opt_seg=6 has fewer duplicates")
        else:
            logger.info("= Both have same duplicate levels")
    
    return report_path


if __name__ == "__main__":
    main()