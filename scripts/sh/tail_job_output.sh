#!/bin/bash
# Quick script to tail the output of the most recent or specified sbatch job

if [[ -n "$1" ]]; then
    JOB_ID="$1"
else
    # Get the most recent job ID
    JOB_ID=$(squeue -u $USER -h -o "%.18i" | sort -rn | head -1)
    
    if [[ -z "$JOB_ID" ]]; then
        echo "❌ No running jobs found"
        echo "Usage: $0 [JOB_ID]"
        exit 1
    fi
fi

OUTPUT_FILE="extract_dimensions_${JOB_ID}.out"
ERROR_FILE="extract_dimensions_${JOB_ID}.err"

echo "📄 Tailing output for job ${JOB_ID}"
echo "📁 Output file: ${OUTPUT_FILE}"
echo "📁 Error file: ${ERROR_FILE}"
echo "Press Ctrl+C to stop"
echo "=================================="
echo ""

# Tail both output and error files
if [[ -f "$OUTPUT_FILE" ]]; then
    tail -f "$OUTPUT_FILE"
else
    echo "⚠️  Output file not found: $OUTPUT_FILE"
    echo "💡 Job may not have started yet. Waiting..."
    
    # Wait a bit and check again
    sleep 2
    
    if [[ -f "$OUTPUT_FILE" ]]; then
        tail -f "$OUTPUT_FILE"
    else
        echo "❌ Output file still not found. Job may have failed or not started."
        if [[ -f "$ERROR_FILE" ]]; then
            echo ""
            echo "Error file contents:"
            cat "$ERROR_FILE"
        fi
        exit 1
    fi
fi



