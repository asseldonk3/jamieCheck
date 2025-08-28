#!/bin/bash
while true; do
    # Count completed results
    count=$(ls -la /home/bramvanasseldonk/jamieCheck/grouptest/results/parallel_result_*.json 2>/dev/null | wc -l)
    echo "$(date '+%H:%M:%S') - Completed: $count/180 parallel results"
    
    # Check if process is still running
    if ! pgrep -f "run_parallel_analysis.py" > /dev/null; then
        echo "Analysis process completed!"
        break
    fi
    
    sleep 60
done
