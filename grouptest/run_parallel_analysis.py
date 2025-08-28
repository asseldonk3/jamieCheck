#!/usr/bin/env python3
"""
Parallel A/B Test Analysis with Worker Pool
Processes 200 URLs using concurrent workers for massive speedup
"""

import os
import sys
import json
import time
import logging
import threading
from pathlib import Path
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple
import pandas as pd

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from ab_test_analyzer_enhanced import EnhancedABTestAnalyzer
import config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [Worker-%(thread)d] - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config.LOGS_DIR / f"parallel_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Thread-safe counters
progress_lock = threading.Lock()
results_lock = threading.Lock()
completed_urls = 0
failed_urls = []
all_results = []


class ParallelWorker:
    """Worker class for parallel URL processing"""
    
    def __init__(self, worker_id: int):
        self.worker_id = worker_id
        self.analyzer = None
        
    def setup(self):
        """Setup worker with its own analyzer instance"""
        self.analyzer = EnhancedABTestAnalyzer()
        self.analyzer.setup_driver()
        logger.info(f"Worker {self.worker_id} initialized")
        
    def cleanup(self):
        """Cleanup worker resources"""
        if self.analyzer:
            self.analyzer.close_driver()
            logger.info(f"Worker {self.worker_id} cleaned up")
    
    def process_url(self, url: str, url_index: int, visits: int) -> Optional[Dict]:
        """Process a single URL"""
        try:
            logger.info(f"Worker {self.worker_id} processing URL {url_index}")
            result = self.analyzer.process_url(url, url_index, visits)
            
            if result:
                # Save individual result file
                result_file = config.RESULTS_DIR / f"parallel_result_{url_index:03d}.json"
                with open(result_file, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                
                logger.info(f"Worker {self.worker_id} completed URL {url_index}")
                return result
            else:
                logger.warning(f"Worker {self.worker_id} failed URL {url_index}")
                return None
                
        except Exception as e:
            logger.error(f"Worker {self.worker_id} error on URL {url_index}: {e}")
            return None


def process_url_batch(worker_id: int, url_batch: List[Tuple[str, int, int]]) -> List[Dict]:
    """Process a batch of URLs with a single worker"""
    worker = ParallelWorker(worker_id)
    batch_results = []
    
    try:
        worker.setup()
        
        for url, url_index, visits in url_batch:
            result = worker.process_url(url, url_index, visits)
            
            if result:
                # Update global progress
                with progress_lock:
                    global completed_urls
                    completed_urls += 1
                    batch_results.append(result)
            else:
                with progress_lock:
                    failed_urls.append(url_index)
                    
    finally:
        worker.cleanup()
    
    return batch_results


def update_progress_display(total_urls: int, start_time: datetime):
    """Display progress in real-time"""
    while completed_urls < total_urls:
        with progress_lock:
            current = completed_urls
            failed = len(failed_urls)
        
        if current > 0:
            elapsed = (datetime.now() - start_time).total_seconds()
            rate = current / elapsed
            remaining = (total_urls - current) / rate if rate > 0 else 0
            eta = timedelta(seconds=int(remaining))
            
            # Progress bar
            progress = current / total_urls
            bar_length = 40
            filled = int(bar_length * progress)
            bar = '#' * filled + '-' * (bar_length - filled)
            
            print(f"\r[{bar}] {current}/{total_urls} URLs ({progress*100:.1f}%) | "
                  f"Failed: {failed} | ETA: {eta} | Rate: {rate*60:.1f} URLs/min", 
                  end='', flush=True)
        
        time.sleep(1)
    
    print()  # New line after completion


def load_urls_for_processing():
    """Load URLs and determine which ones need processing"""
    # Load all URLs from Excel
    df = pd.read_excel(config.INPUT_FILE)
    total_urls = len(df)
    logger.info(f"Loaded {total_urls} URLs from Excel")
    
    # Check existing results
    existing_results = set()
    results_dir = Path(config.RESULTS_DIR)
    
    # Check both enhanced and parallel result files
    for pattern in ['enhanced_result_*.json', 'parallel_result_*.json']:
        for result_file in results_dir.glob(pattern):
            try:
                idx = int(result_file.stem.split('_')[-1])
                existing_results.add(idx)
            except:
                pass
    
    logger.info(f"Found {len(existing_results)} already processed URLs")
    
    # Prepare URLs for processing
    urls_to_process = []
    for index, row in df.iterrows():
        url_index = index + 1
        if url_index not in existing_results:
            urls_to_process.append((
                row['url'],
                url_index,
                row.get('visits', 0)
            ))
    
    logger.info(f"Will process {len(urls_to_process)} remaining URLs")
    return urls_to_process, total_urls


def run_parallel_analysis(num_workers: int = 6):
    """Main parallel analysis function"""
    
    logger.info("=" * 80)
    logger.info("STARTING PARALLEL A/B TEST ANALYSIS")
    logger.info(f"Number of workers: {num_workers}")
    logger.info("=" * 80)
    
    # Load URLs
    urls_to_process, total_urls = load_urls_for_processing()
    
    if not urls_to_process:
        logger.info("All URLs have been processed!")
        return
    
    # Split URLs into batches for workers
    batch_size = len(urls_to_process) // num_workers + 1
    url_batches = [
        urls_to_process[i:i + batch_size] 
        for i in range(0, len(urls_to_process), batch_size)
    ]
    
    logger.info(f"Created {len(url_batches)} batches for processing")
    
    # Start progress display thread
    start_time = datetime.now()
    progress_thread = threading.Thread(
        target=update_progress_display, 
        args=(len(urls_to_process), start_time)
    )
    progress_thread.daemon = True
    progress_thread.start()
    
    # Process URLs in parallel
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = {
            executor.submit(process_url_batch, i+1, batch): i 
            for i, batch in enumerate(url_batches)
        }
        
        for future in as_completed(futures):
            worker_id = futures[future]
            try:
                batch_results = future.result()
                with results_lock:
                    all_results.extend(batch_results)
                logger.info(f"Worker batch {worker_id + 1} completed with {len(batch_results)} results")
            except Exception as e:
                logger.error(f"Worker batch {worker_id + 1} failed: {e}")
    
    # Wait for progress display to finish
    time.sleep(2)
    
    # Compile final results
    compile_final_results()
    
    # Report completion
    elapsed = datetime.now() - start_time
    logger.info("=" * 80)
    logger.info("PARALLEL ANALYSIS COMPLETE")
    logger.info(f"Total time: {elapsed}")
    logger.info(f"Processed: {completed_urls} URLs")
    logger.info(f"Failed: {len(failed_urls)} URLs")
    logger.info(f"Average rate: {completed_urls / elapsed.total_seconds() * 60:.1f} URLs/minute")
    logger.info("=" * 80)
    
    if failed_urls:
        logger.info(f"Failed URL indices: {sorted(failed_urls)}")


def compile_final_results():
    """Compile all results into final files"""
    logger.info("Compiling final results...")
    
    # Load all individual result files
    final_results = []
    results_dir = Path(config.RESULTS_DIR)
    
    for pattern in ['enhanced_result_*.json', 'parallel_result_*.json']:
        for result_file in sorted(results_dir.glob(pattern)):
            try:
                with open(result_file, 'r') as f:
                    result = json.load(f)
                    final_results.append(result)
            except Exception as e:
                logger.error(f"Failed to load {result_file}: {e}")
    
    # Sort by URL index
    final_results.sort(key=lambda x: x['url_index'])
    
    # Save compiled results
    compiled_file = results_dir / "all_parallel_results.json"
    with open(compiled_file, 'w', encoding='utf-8') as f:
        json.dump(final_results, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Compiled {len(final_results)} results to {compiled_file}")
    
    # Calculate statistics
    calculate_final_statistics(final_results)


def calculate_final_statistics(results: List[Dict]):
    """Calculate comprehensive statistics"""
    
    if not results:
        logger.warning("No results to calculate statistics")
        return
    
    # Basic winner statistics
    wins_a = sum(1 for r in results if r['analysis']['winner'] == 'A')
    wins_b = sum(1 for r in results if r['analysis']['winner'] == 'B')
    ties = sum(1 for r in results if r['analysis']['winner'] == 'Tie')
    
    # Duplicate statistics
    total_duplicates_a = sum(
        r['variant_a'].get('duplicates', 0) 
        for r in results 
        if r['variant_a'].get('duplicates', -1) >= 0
    )
    total_duplicates_b = sum(
        r['variant_b'].get('duplicates', 0) 
        for r in results 
        if r['variant_b'].get('duplicates', -1) >= 0
    )
    
    valid_duplicate_count = len([
        r for r in results 
        if r['variant_a'].get('duplicates', -1) >= 0
    ])
    
    avg_duplicates_a = total_duplicates_a / valid_duplicate_count if valid_duplicate_count else 0
    avg_duplicates_b = total_duplicates_b / valid_duplicate_count if valid_duplicate_count else 0
    
    # Confidence statistics
    avg_confidence = sum(
        r['analysis'].get('confidence', 0.5) 
        for r in results
    ) / len(results)
    
    # Score statistics
    avg_score_a = sum(
        r['variant_a'].get('score', 0) 
        for r in results
    ) / len(results)
    avg_score_b = sum(
        r['variant_b'].get('score', 0) 
        for r in results
    ) / len(results)
    
    stats = {
        "total_urls_analyzed": len(results),
        "variant_a_wins": wins_a,
        "variant_b_wins": wins_b,
        "ties": ties,
        "win_percentage_a": round(wins_a / len(results) * 100, 1),
        "win_percentage_b": round(wins_b / len(results) * 100, 1),
        "tie_percentage": round(ties / len(results) * 100, 1),
        "average_confidence": round(avg_confidence, 3),
        "average_score_a": round(avg_score_a, 2),
        "average_score_b": round(avg_score_b, 2),
        "average_duplicates_a": round(avg_duplicates_a, 2),
        "average_duplicates_b": round(avg_duplicates_b, 2),
        "total_duplicates_a": total_duplicates_a,
        "total_duplicates_b": total_duplicates_b,
        "duplicate_difference": round(avg_duplicates_b - avg_duplicates_a, 2),
        "overall_winner": "A (opt_seg=5)" if wins_a > wins_b else "B (opt_seg=6)" if wins_b > wins_a else "Tie",
        "recommendation": generate_recommendation(wins_a, wins_b, avg_duplicates_a, avg_duplicates_b)
    }
    
    # Save statistics
    stats_file = config.RESULTS_DIR / "parallel_statistics.json"
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    
    # Print summary
    print("\n" + "=" * 80)
    print("FINAL ANALYSIS RESULTS")
    print("=" * 80)
    print(f"Total URLs analyzed: {stats['total_urls_analyzed']}")
    print(f"")
    print(f"WINNER DISTRIBUTION:")
    print(f"  Variant A (opt_seg=5): {wins_a} wins ({stats['win_percentage_a']}%)")
    print(f"  Variant B (opt_seg=6): {wins_b} wins ({stats['win_percentage_b']}%)")
    print(f"  Ties: {ties} ({stats['tie_percentage']}%)")
    print(f"")
    print(f"QUALITY SCORES:")
    print(f"  Average Score A: {stats['average_score_a']}/10")
    print(f"  Average Score B: {stats['average_score_b']}/10")
    print(f"  Average Confidence: {stats['average_confidence']}")
    print(f"")
    print(f"DUPLICATE ANALYSIS:")
    print(f"  Average Duplicates in A: {stats['average_duplicates_a']}")
    print(f"  Average Duplicates in B: {stats['average_duplicates_b']}")
    print(f"  Difference (B-A): {stats['duplicate_difference']}")
    print(f"")
    print(f"OVERALL WINNER: {stats['overall_winner']}")
    print(f"")
    print(f"RECOMMENDATION:")
    print(f"  {stats['recommendation']}")
    print("=" * 80)


def generate_recommendation(wins_a: int, wins_b: int, avg_dup_a: float, avg_dup_b: float) -> str:
    """Generate recommendation based on results"""
    
    if wins_a > wins_b * 1.2:  # A wins by >20%
        if avg_dup_a < avg_dup_b:
            return "Strongly recommend opt_seg=5 (better rankings AND fewer duplicates)"
        else:
            return "Recommend opt_seg=5 (significantly better rankings despite more duplicates)"
    elif wins_b > wins_a * 1.2:  # B wins by >20%
        if avg_dup_b < avg_dup_a:
            return "Strongly recommend opt_seg=6 (better rankings AND fewer duplicates)"
        else:
            return "Recommend opt_seg=6 (significantly better rankings despite more duplicates)"
    else:  # Close results
        if abs(avg_dup_a - avg_dup_b) > 1:  # Significant duplicate difference
            if avg_dup_a < avg_dup_b:
                return "Slight preference for opt_seg=5 (similar quality but fewer duplicates)"
            else:
                return "Slight preference for opt_seg=6 (similar quality but fewer duplicates)"
        else:
            return "No clear winner - both algorithms perform similarly. Consider A/B testing in production."


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Parallel A/B test analysis')
    parser.add_argument('--workers', type=int, default=6, help='Number of parallel workers (default: 6)')
    parser.add_argument('--retry-failed', action='store_true', help='Retry only failed URLs')
    
    args = parser.parse_args()
    
    # Create necessary directories
    config.SCREENSHOTS_DIR.mkdir(exist_ok=True, parents=True)
    config.RESULTS_DIR.mkdir(exist_ok=True, parents=True)
    config.LOGS_DIR.mkdir(exist_ok=True, parents=True)
    
    # Run analysis
    run_parallel_analysis(num_workers=args.workers)


if __name__ == "__main__":
    main()