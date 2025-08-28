#!/usr/bin/env python3
"""
Monitor progress of A/B test analysis
"""

import time
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta

def monitor_progress():
    """Monitor the analysis progress"""
    
    results_dir = Path("results")
    log_file = Path("full_analysis.log")
    
    print("\n" + "="*60)
    print("A/B TEST ANALYSIS PROGRESS MONITOR")
    print("="*60)
    
    start_time = datetime.now()
    last_count = 0
    
    while True:
        try:
            # Count result files
            result_files = list(results_dir.glob("result_*.json"))
            current_count = len(result_files)
            
            # Get latest from log
            if log_file.exists():
                with open(log_file, 'r') as f:
                    lines = f.readlines()
                    for line in reversed(lines):
                        if "Processing URL" in line:
                            latest = line.strip()
                            break
                    else:
                        latest = "No processing info found"
            else:
                latest = "Log file not found"
            
            # Calculate stats
            elapsed = datetime.now() - start_time
            if current_count > last_count:
                rate = elapsed.total_seconds() / current_count if current_count > 0 else 0
                remaining = (200 - current_count) * rate
                eta = datetime.now() + timedelta(seconds=remaining)
            else:
                eta = None
                rate = 0
            
            # Display progress
            print(f"\r[{datetime.now().strftime('%H:%M:%S')}] "
                  f"Completed: {current_count}/200 ({current_count/2:.0f}%) | "
                  f"Rate: {rate:.1f}s/URL | "
                  f"ETA: {eta.strftime('%H:%M:%S') if eta else 'calculating...'}", 
                  end='', flush=True)
            
            if current_count != last_count:
                print(f"\n  Latest: {latest}")
                last_count = current_count
            
            # Check if complete
            if current_count >= 200:
                print(f"\n\n✓ Analysis complete! All 200 URLs processed.")
                break
            
            # Check for report generation
            pdf_files = list(Path(".").glob("ab_test_report_*.pdf"))
            if pdf_files:
                latest_pdf = max(pdf_files, key=lambda p: p.stat().st_mtime)
                if (datetime.now() - datetime.fromtimestamp(latest_pdf.stat().st_mtime)).seconds < 60:
                    print(f"\n\n✓ Report generated: {latest_pdf}")
                    break
            
            time.sleep(5)
            
        except KeyboardInterrupt:
            print("\n\nMonitoring stopped by user.")
            break
        except Exception as e:
            print(f"\nError: {e}")
            time.sleep(5)

if __name__ == "__main__":
    monitor_progress()