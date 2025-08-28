#!/usr/bin/env python3
"""
Run the complete enhanced A/B test analysis with automatic resumption
Processes all 200 URLs with duplicate detection using GPT-5-mini
"""

import sys
import logging
import time
import json
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from ab_test_analyzer_enhanced import EnhancedABTestAnalyzer
from report_generator import ABTestReportGenerator
import config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_processed_count():
    """Get the number of already processed URLs"""
    results_file = config.RESULTS_DIR / "enhanced_results.json"
    if results_file.exists():
        with open(results_file, 'r') as f:
            data = json.load(f)
            return len(data)
    return 0


def run_with_resumption(total_urls=200, batch_size=10):
    """Run analysis with automatic resumption"""
    
    while True:
        processed = get_processed_count()
        
        if processed >= total_urls:
            logger.info(f"All {total_urls} URLs have been processed!")
            break
            
        remaining = total_urls - processed
        next_batch = min(batch_size, remaining)
        start_from = processed + 1 if processed > 0 else None
        
        logger.info("=" * 80)
        logger.info(f"RESUMING ANALYSIS: {processed}/{total_urls} completed")
        logger.info(f"Processing next {next_batch} URLs (starting from URL {start_from or 1})")
        logger.info("=" * 80)
        
        try:
            analyzer = EnhancedABTestAnalyzer()
            
            # Run analysis for the next batch
            results = analyzer.run_analysis(
                limit=next_batch if start_from else next_batch,
                start_from=start_from
            )
            
            logger.info(f"Batch completed successfully: {len(results)} URLs processed")
            
        except Exception as e:
            logger.error(f"Batch failed with error: {e}")
            logger.info("Waiting 30 seconds before retrying...")
            time.sleep(30)
            continue
        
        # Small delay between batches to avoid overwhelming the API
        if remaining > next_batch:
            logger.info("Waiting 10 seconds before next batch...")
            time.sleep(10)
    
    return True


def generate_enhanced_report():
    """Generate the enhanced PDF report with duplicate analysis"""
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    logger.info("=" * 80)
    logger.info("GENERATING ENHANCED PDF REPORT")
    logger.info("=" * 80)
    
    results_file = config.RESULTS_DIR / "enhanced_results.json"
    
    if not results_file.exists():
        logger.error(f"Results file not found: {results_file}")
        return False
    
    try:
        # Load results
        with open(results_file, 'r') as f:
            results = json.load(f)
        
        # Generate report using existing report generator
        generator = ABTestReportGenerator(results_file)
        output_file = config.BASE_DIR / f"enhanced_ab_test_report_{timestamp}.pdf"
        report_path = generator.generate_report(output_file)
        
        logger.info(f"Enhanced report generated: {report_path}")
        return report_path
        
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        return False


def analyze_results():
    """Analyze all results and provide comprehensive feedback"""
    
    results_file = config.RESULTS_DIR / "enhanced_results.json"
    stats_file = config.RESULTS_DIR / "enhanced_statistics.json"
    
    with open(results_file, 'r') as f:
        results = json.load(f)
    
    if stats_file.exists():
        with open(stats_file, 'r') as f:
            stats = json.load(f)
    else:
        stats = {}
    
    logger.info("\n" + "=" * 80)
    logger.info("COMPREHENSIVE ANALYSIS RESULTS")
    logger.info("=" * 80)
    
    # Overall statistics
    total_urls = len(results)
    wins_a = sum(1 for r in results if r['analysis']['winner'] == 'A')
    wins_b = sum(1 for r in results if r['analysis']['winner'] == 'B')
    ties = sum(1 for r in results if r['analysis']['winner'] == 'Tie')
    
    logger.info(f"\nOVERALL WINNER DISTRIBUTION:")
    logger.info(f"  Total URLs Analyzed: {total_urls}")
    logger.info(f"  Variant A (opt_seg=5) Wins: {wins_a} ({wins_a/total_urls*100:.1f}%)")
    logger.info(f"  Variant B (opt_seg=6) Wins: {wins_b} ({wins_b/total_urls*100:.1f}%)")
    logger.info(f"  Ties: {ties} ({ties/total_urls*100:.1f}%)")
    
    # Duplicate analysis
    urls_with_duplicates_a = sum(1 for r in results if r['variant_a']['duplicates'] > 0)
    urls_with_duplicates_b = sum(1 for r in results if r['variant_b']['duplicates'] > 0)
    
    total_duplicates_a = sum(r['variant_a']['duplicates'] for r in results if r['variant_a']['duplicates'] >= 0)
    total_duplicates_b = sum(r['variant_b']['duplicates'] for r in results if r['variant_b']['duplicates'] >= 0)
    
    logger.info(f"\nDUPLICATE PRODUCT ANALYSIS:")
    logger.info(f"  URLs with duplicates in A: {urls_with_duplicates_a} ({urls_with_duplicates_a/total_urls*100:.1f}%)")
    logger.info(f"  URLs with duplicates in B: {urls_with_duplicates_b} ({urls_with_duplicates_b/total_urls*100:.1f}%)")
    logger.info(f"  Total duplicates found in A: {total_duplicates_a}")
    logger.info(f"  Total duplicates found in B: {total_duplicates_b}")
    
    if total_duplicates_a != total_duplicates_b:
        reduction = ((total_duplicates_b - total_duplicates_a) / total_duplicates_b * 100) if total_duplicates_b > 0 else 0
        logger.info(f"  Duplicate reduction by opt_seg=5: {reduction:.1f}%")
    
    # Find interesting cases
    logger.info(f"\nINTERESTING CASES:")
    
    # URLs where A reduces duplicates
    duplicate_wins = [r for r in results 
                     if r['variant_a']['duplicates'] < r['variant_b']['duplicates'] 
                     and r['variant_b']['duplicates'] > 0]
    
    if duplicate_wins:
        logger.info(f"\n  URLs where opt_seg=5 reduces duplicates: {len(duplicate_wins)}")
        for r in duplicate_wins[:3]:  # Show first 3 examples
            logger.info(f"    - URL {r['url_index']}: {r['variant_a']['duplicates']} vs {r['variant_b']['duplicates']} duplicates")
    
    # High confidence winners
    high_confidence = [r for r in results if r['analysis']['confidence'] >= 0.9 and r['analysis']['winner'] != 'Tie']
    if high_confidence:
        logger.info(f"\n  High confidence winners (≥90%): {len(high_confidence)}")
        for r in high_confidence[:3]:
            logger.info(f"    - URL {r['url_index']}: {r['analysis']['winner']} wins ({r['analysis']['confidence']*100:.0f}%)")
    
    # Average scores
    avg_score_a = sum(r['variant_a']['score'] for r in results) / len(results) if results else 0
    avg_score_b = sum(r['variant_b']['score'] for r in results) / len(results) if results else 0
    
    logger.info(f"\nAVERAGE RANKING QUALITY SCORES:")
    logger.info(f"  Variant A: {avg_score_a:.2f}/10")
    logger.info(f"  Variant B: {avg_score_b:.2f}/10")
    
    logger.info("\n" + "=" * 80)
    
    return results


def main():
    """Main execution function"""
    
    logger.info("=" * 80)
    logger.info("STARTING FULL ENHANCED ANALYSIS WITH AUTOMATIC RESUMPTION")
    logger.info("=" * 80)
    logger.info(f"Target: 200 URLs")
    logger.info(f"Model: {config.OPENAI_MODEL}")
    logger.info(f"Batch size: 10 URLs")
    logger.info("=" * 80)
    
    # Step 1: Run analysis with resumption
    success = run_with_resumption(total_urls=200, batch_size=10)
    
    if not success:
        logger.error("Analysis failed to complete")
        return False
    
    # Step 2: Generate PDF report
    report_path = generate_enhanced_report()
    
    if not report_path:
        logger.error("Report generation failed")
        return False
    
    # Step 3: Analyze and provide feedback
    analyze_results()
    
    logger.info("\n" + "=" * 80)
    logger.info("FULL ANALYSIS COMPLETE!")
    logger.info(f"Report available at: {report_path}")
    logger.info("=" * 80)
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)