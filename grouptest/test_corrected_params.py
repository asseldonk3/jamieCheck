#!/usr/bin/env python3
"""
Quick test to verify the corrected parameters produce different results
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from ab_test_analyzer_enhanced import EnhancedABTestAnalyzer
import config
import json

print("=" * 80)
print("TESTING CORRECTED PARAMETERS - Quick Verification")
print("=" * 80)
print()

# Initialize analyzer
analyzer = EnhancedABTestAnalyzer()

try:
    # Test just 3 URLs to verify differences
    test_urls = [
        "https://www.beslist.nl/products/fietsen/",
        "https://www.beslist.nl/products/mode/",
        "https://www.beslist.nl/products/main_sanitair/"
    ]
    
    print(f"Testing {len(test_urls)} URLs with corrected parameters...")
    print(f"Variant A: opt_seg={config.VARIANT_A_PARAM}")
    print(f"Variant B: opt_seg={config.VARIANT_B_PARAM}")
    print()
    
    analyzer.setup_driver()
    
    for idx, url in enumerate(test_urls, 1):
        print(f"\nTesting URL {idx}: {url}")
        
        # Create proper URLs with corrected parameters
        url_a = analyzer.modify_url_with_param(url, config.VARIANT_A_PARAM)
        url_b = analyzer.modify_url_with_param(url, config.VARIANT_B_PARAM)
        
        print(f"  Variant A: {url_a}")
        print(f"  Variant B: {url_b}")
        
        # Capture and analyze
        result = analyzer.process_url(url, idx, visits=0)
        
        if result:
            winner = result['analysis']['winner']
            confidence = result['analysis'].get('confidence', 0)
            key_diff = result['analysis'].get('key_differences', 'No differences noted')
            
            print(f"  Result: Winner = {winner}, Confidence = {confidence:.2f}")
            print(f"  Key Differences: {key_diff[:100]}...")
            
            if winner != "Tie":
                print(f"  ✅ SEGMENTS ARE NOW DIFFERENT!")
            else:
                print(f"  ⚠️  Still showing as Tie")
        else:
            print(f"  ❌ Analysis failed")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
    
finally:
    analyzer.close_driver()