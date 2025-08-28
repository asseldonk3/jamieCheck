#!/usr/bin/env python3
"""
Auto-complete script that monitors the parallel analysis and generates report when done
"""

import time
import json
import subprocess
from pathlib import Path
from datetime import datetime
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))
import config


def count_results():
    """Count all processed results"""
    results_dir = Path(config.RESULTS_DIR)
    total_count = 0
    
    # Count enhanced results
    enhanced_results = list(results_dir.glob("enhanced_result_*.json"))
    parallel_results = list(results_dir.glob("parallel_result_*.json"))
    
    # Get unique URL indices
    processed = set()
    for f in enhanced_results + parallel_results:
        try:
            idx = int(f.stem.split('_')[-1])
            processed.add(idx)
        except:
            pass
    
    return len(processed)


def is_analysis_running():
    """Check if the parallel analysis is still running"""
    try:
        result = subprocess.run(['pgrep', '-f', 'run_parallel_analysis.py'], 
                              capture_output=True, text=True)
        return result.returncode == 0
    except:
        return False


def compile_all_results():
    """Compile all results into a single file"""
    print("Compiling all results...")
    
    results_dir = Path(config.RESULTS_DIR)
    all_results = []
    
    # Load all individual result files
    for pattern in ['enhanced_result_*.json', 'parallel_result_*.json']:
        for result_file in sorted(results_dir.glob(pattern)):
            try:
                with open(result_file, 'r') as f:
                    result = json.load(f)
                    all_results.append(result)
            except Exception as e:
                print(f"Failed to load {result_file}: {e}")
    
    # Remove duplicates based on url_index
    unique_results = {}
    for r in all_results:
        url_idx = r.get('url_index')
        if url_idx:
            unique_results[url_idx] = r
    
    # Sort by URL index
    final_results = sorted(unique_results.values(), key=lambda x: x['url_index'])
    
    # Save compiled results
    output_file = results_dir / "final_200_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(final_results, f, ensure_ascii=False, indent=2)
    
    print(f"Compiled {len(final_results)} unique results to {output_file}")
    return output_file, final_results


def calculate_comprehensive_stats(results):
    """Calculate detailed statistics"""
    
    # Basic winner statistics
    wins_a = sum(1 for r in results if r['analysis']['winner'] == 'A')
    wins_b = sum(1 for r in results if r['analysis']['winner'] == 'B')
    ties = sum(1 for r in results if r['analysis']['winner'] == 'Tie')
    
    # Duplicate statistics
    duplicates_data_a = [r['variant_a'].get('duplicates', 0) for r in results 
                         if r['variant_a'].get('duplicates', -1) >= 0]
    duplicates_data_b = [r['variant_b'].get('duplicates', 0) for r in results 
                         if r['variant_b'].get('duplicates', -1) >= 0]
    
    avg_duplicates_a = sum(duplicates_data_a) / len(duplicates_data_a) if duplicates_data_a else 0
    avg_duplicates_b = sum(duplicates_data_b) / len(duplicates_data_b) if duplicates_data_b else 0
    
    # Confidence statistics
    confidences = [r['analysis'].get('confidence', 0.5) for r in results]
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0
    
    # Score statistics
    scores_a = [r['variant_a'].get('score', 0) for r in results]
    scores_b = [r['variant_b'].get('score', 0) for r in results]
    avg_score_a = sum(scores_a) / len(scores_a) if scores_a else 0
    avg_score_b = sum(scores_b) / len(scores_b) if scores_b else 0
    
    # High confidence wins
    high_conf_a = sum(1 for r in results if r['analysis']['winner'] == 'A' 
                      and r['analysis'].get('confidence', 0) > 0.8)
    high_conf_b = sum(1 for r in results if r['analysis']['winner'] == 'B'
                      and r['analysis'].get('confidence', 0) > 0.8)
    
    stats = {
        "analysis_complete": True,
        "total_urls_analyzed": len(results),
        "variant_a_wins": wins_a,
        "variant_b_wins": wins_b,
        "ties": ties,
        "win_percentage_a": round(wins_a / len(results) * 100, 1),
        "win_percentage_b": round(wins_b / len(results) * 100, 1),
        "tie_percentage": round(ties / len(results) * 100, 1),
        "high_confidence_wins_a": high_conf_a,
        "high_confidence_wins_b": high_conf_b,
        "average_confidence": round(avg_confidence, 3),
        "confidence_std": round(sum((c - avg_confidence)**2 for c in confidences)**0.5 / len(confidences), 3),
        "average_score_a": round(avg_score_a, 2),
        "average_score_b": round(avg_score_b, 2),
        "score_difference": round(avg_score_b - avg_score_a, 2),
        "average_duplicates_a": round(avg_duplicates_a, 2),
        "average_duplicates_b": round(avg_duplicates_b, 2),
        "total_duplicates_a": sum(duplicates_data_a),
        "total_duplicates_b": sum(duplicates_data_b),
        "duplicate_difference": round(avg_duplicates_b - avg_duplicates_a, 2),
        "overall_winner": determine_winner(wins_a, wins_b, avg_duplicates_a, avg_duplicates_b),
        "statistical_significance": calculate_significance(wins_a, wins_b, len(results)),
        "recommendation": generate_detailed_recommendation(
            wins_a, wins_b, avg_duplicates_a, avg_duplicates_b, 
            avg_score_a, avg_score_b, high_conf_a, high_conf_b
        )
    }
    
    # Save statistics
    stats_file = config.RESULTS_DIR / "final_200_statistics.json"
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    
    return stats


def determine_winner(wins_a, wins_b, dup_a, dup_b):
    """Determine overall winner with detailed reasoning"""
    
    if wins_a > wins_b * 1.15:  # A wins by >15%
        return f"Variant A (opt_seg=5) - Clear winner with {wins_a} wins"
    elif wins_b > wins_a * 1.15:  # B wins by >15%
        return f"Variant B (opt_seg=6) - Clear winner with {wins_b} wins"
    elif abs(wins_a - wins_b) <= 5:  # Very close
        if abs(dup_a - dup_b) > 0.5:
            if dup_a < dup_b:
                return f"Variant A (opt_seg=5) - Marginal win with fewer duplicates"
            else:
                return f"Variant B (opt_seg=6) - Marginal win with fewer duplicates"
        return "Statistical Tie - No clear winner"
    else:
        if wins_a > wins_b:
            return f"Variant A (opt_seg=5) - Slight advantage with {wins_a} wins"
        else:
            return f"Variant B (opt_seg=6) - Slight advantage with {wins_b} wins"


def calculate_significance(wins_a, wins_b, total):
    """Calculate statistical significance of results"""
    
    # Simple binomial test approximation
    expected = total / 2
    observed = max(wins_a, wins_b)
    
    # Z-score calculation
    std_dev = (total * 0.5 * 0.5) ** 0.5
    z_score = abs(observed - expected) / std_dev if std_dev > 0 else 0
    
    if z_score > 2.58:
        return "Highly significant (99% confidence)"
    elif z_score > 1.96:
        return "Significant (95% confidence)"
    elif z_score > 1.64:
        return "Marginally significant (90% confidence)"
    else:
        return "Not statistically significant"


def generate_detailed_recommendation(wins_a, wins_b, dup_a, dup_b, score_a, score_b, high_a, high_b):
    """Generate detailed recommendation based on all metrics"""
    
    recommendations = []
    
    # Primary recommendation based on wins
    if wins_a > wins_b * 1.2:
        recommendations.append("STRONG RECOMMENDATION: Implement opt_seg=5 (Variant A)")
        recommendations.append(f"Variant A shows {((wins_a/wins_b - 1) * 100):.1f}% better performance")
    elif wins_b > wins_a * 1.2:
        recommendations.append("STRONG RECOMMENDATION: Implement opt_seg=6 (Variant B)")
        recommendations.append(f"Variant B shows {((wins_b/wins_a - 1) * 100):.1f}% better performance")
    else:
        recommendations.append("RECOMMENDATION: Consider extended A/B testing in production")
        recommendations.append("Results show no clear winner between variants")
    
    # Duplicate analysis
    if abs(dup_a - dup_b) > 0.5:
        if dup_a < dup_b:
            recommendations.append(f"Variant A shows {abs(dup_a - dup_b):.1f} fewer duplicates per page (better diversity)")
        else:
            recommendations.append(f"Variant B shows {abs(dup_a - dup_b):.1f} fewer duplicates per page (better diversity)")
    
    # Quality score analysis
    if abs(score_a - score_b) > 0.5:
        if score_a > score_b:
            recommendations.append(f"Variant A has {abs(score_a - score_b):.1f} points higher quality score")
        else:
            recommendations.append(f"Variant B has {abs(score_a - score_b):.1f} points higher quality score")
    
    # High confidence analysis
    if high_a + high_b > 0:
        recommendations.append(f"High confidence wins: A={high_a}, B={high_b}")
    
    return " | ".join(recommendations)


def generate_final_report():
    """Generate the comprehensive PDF report"""
    print("\nGenerating comprehensive PDF report...")
    
    try:
        # Import the report generator
        from generate_full_report import ComprehensiveReportGenerator
        
        generator = ComprehensiveReportGenerator()
        
        # Use the final compiled results
        results_file = config.RESULTS_DIR / "final_200_results.json"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = config.BASE_DIR / f"final_200_analysis_report_{timestamp}.pdf"
        
        report_path = generator.generate_report(
            results_file=str(results_file),
            output_file=str(output_file)
        )
        
        if report_path:
            print(f"\n✅ PDF Report generated successfully: {report_path}")
            return report_path
        else:
            print("\n❌ Failed to generate PDF report")
            return None
            
    except Exception as e:
        print(f"\n❌ Error generating report: {e}")
        return None


def print_final_summary(stats):
    """Print comprehensive final summary"""
    
    print("\n" + "=" * 80)
    print("🎯 FINAL ANALYSIS COMPLETE - 200 URLs ANALYZED")
    print("=" * 80)
    
    print(f"\n📊 WINNER DISTRIBUTION:")
    print(f"  Variant A (opt_seg=5): {stats['variant_a_wins']} wins ({stats['win_percentage_a']}%)")
    print(f"  Variant B (opt_seg=6): {stats['variant_b_wins']} wins ({stats['win_percentage_b']}%)")
    print(f"  Ties: {stats['ties']} ({stats['tie_percentage']}%)")
    
    print(f"\n📈 QUALITY METRICS:")
    print(f"  Average Score A: {stats['average_score_a']}/10")
    print(f"  Average Score B: {stats['average_score_b']}/10")
    print(f"  Score Difference: {stats['score_difference']}")
    print(f"  Average Confidence: {stats['average_confidence']}")
    
    print(f"\n🔍 DUPLICATE ANALYSIS:")
    print(f"  Average Duplicates A: {stats['average_duplicates_a']}")
    print(f"  Average Duplicates B: {stats['average_duplicates_b']}")
    print(f"  Total Duplicates A: {stats['total_duplicates_a']}")
    print(f"  Total Duplicates B: {stats['total_duplicates_b']}")
    
    print(f"\n🏆 OVERALL WINNER: {stats['overall_winner']}")
    print(f"📊 Statistical Significance: {stats['statistical_significance']}")
    
    print(f"\n💡 RECOMMENDATION:")
    for line in stats['recommendation'].split(' | '):
        print(f"  • {line}")
    
    print("\n" + "=" * 80)


def main():
    """Main monitoring and completion function"""
    
    print("=" * 80)
    print("AUTO-COMPLETION MONITOR STARTED")
    print("Waiting for parallel analysis to complete all 200 URLs...")
    print("=" * 80)
    
    last_count = 0
    start_time = time.time()
    
    while True:
        current_count = count_results()
        
        # Print progress if changed
        if current_count != last_count:
            elapsed = time.time() - start_time
            rate = current_count / (elapsed / 60) if elapsed > 0 else 0
            remaining = (200 - current_count) / rate if rate > 0 else 0
            
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Progress: {current_count}/200 URLs completed")
            print(f"  Rate: {rate:.1f} URLs/min | ETA: {remaining:.1f} minutes")
            last_count = current_count
        
        # Check if analysis is complete
        if current_count >= 200:
            print("\n✅ All 200 URLs have been processed!")
            break
        
        # Check if analysis is still running
        if not is_analysis_running() and current_count < 200:
            print(f"\n⚠️ Analysis stopped at {current_count} URLs. Proceeding with available data...")
            if current_count < 100:
                print("Warning: Less than 100 URLs analyzed. Results may not be representative.")
            break
        
        # Wait before next check
        time.sleep(30)
    
    # Compile and analyze results
    print("\n📋 Compiling final results...")
    results_file, results_data = compile_all_results()
    
    print("\n📊 Calculating comprehensive statistics...")
    stats = calculate_comprehensive_stats(results_data)
    
    # Print summary
    print_final_summary(stats)
    
    # Generate PDF report
    report_path = generate_final_report()
    
    print("\n✅ ANALYSIS PIPELINE COMPLETE!")
    print(f"  • Results: {results_file}")
    print(f"  • Statistics: {config.RESULTS_DIR / 'final_200_statistics.json'}")
    if report_path:
        print(f"  • PDF Report: {report_path}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())