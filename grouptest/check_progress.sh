#!/bin/bash

# Quick progress checker for A/B test analysis

echo "========================================"
echo "A/B TEST ANALYSIS PROGRESS"
echo "========================================"
echo ""

# Count completed results
COMPLETED=$(find results -name "result_*.json" 2>/dev/null | wc -l)
echo "URLs Processed: $COMPLETED / 200 ($(( COMPLETED * 100 / 200 ))%)"

# Get latest from log
if [ -f full_analysis.log ]; then
    LATEST=$(tail -100 full_analysis.log | grep "Processing URL" | tail -1)
    echo "Latest: $LATEST"
fi

# Check if process is running
if pgrep -f "run_ab_test.py" > /dev/null; then
    echo "Status: ✓ Analysis is running"
else
    echo "Status: ⚠ Analysis process not found"
fi

# Estimate time remaining
if [ "$COMPLETED" -gt 0 ]; then
    # Assuming ~15-20 seconds per URL
    REMAINING=$((200 - COMPLETED))
    EST_MINUTES=$(( REMAINING * 20 / 60 ))
    EST_HOURS=$(( EST_MINUTES / 60 ))
    EST_MINS_LEFT=$(( EST_MINUTES % 60 ))
    
    echo ""
    echo "Estimated time remaining: ${EST_HOURS}h ${EST_MINS_LEFT}m"
    echo "(assuming ~20 seconds per URL)"
fi

echo ""
echo "========================================"
echo "To monitor live: tail -f full_analysis.log"
echo "To generate report from current results:"
echo "  python3 run_ab_test.py --skip-analysis"