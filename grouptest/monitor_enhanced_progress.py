#!/usr/bin/env python3
"""Monitor progress of enhanced analysis"""

import json
import time
from pathlib import Path
from datetime import datetime

def get_progress():
    results_file = Path("results/enhanced_results.json")
    if results_file.exists():
        with open(results_file, 'r') as f:
            data = json.load(f)
            return len(data)
    return 0

def main():
    print("=" * 60)
    print("ENHANCED ANALYSIS PROGRESS MONITOR")
    print("=" * 60)
    
    while True:
        processed = get_progress()
        percentage = (processed / 200) * 100
        
        print(f"\r[{datetime.now().strftime('%H:%M:%S')}] Progress: {processed}/200 URLs ({percentage:.1f}%) ", end="", flush=True)
        
        if processed >= 200:
            print("\n\n✅ ANALYSIS COMPLETE!")
            break
        
        time.sleep(30)  # Check every 30 seconds

if __name__ == "__main__":
    main()