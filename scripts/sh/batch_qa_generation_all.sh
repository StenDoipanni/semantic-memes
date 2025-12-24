#!/bin/bash

# Batch Q&A Generation Script for ALL 1000 memes
# Processes all TTL files for Q&A generation with detailed monitoring
# Runs in background with logging

set +e  # Don't exit on error, continue processing other files

# Configuration
OUTPUT_REVERSED_DIR="/home/stefano/memes/semantic-memes/output_reversed/hateful-memes-out"
OUTPUT_DIR="/home/stefano/memes/semantic-memes/output_reversed/hateful_memes_out_final"
LLM_PROVIDER="huggingface"
LLM_MODEL="Qwen/Qwen3-VL-8B-Instruct"
IMG_DIR="/home/stefano/memes/semantic-memes/img/hateful-memes-img"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
LOG_FILE="$REPO_ROOT/output_reversed/qa_generation_all.log"
PROGRESS_FILE="$REPO_ROOT/output_reversed/qa_generation_progress.txt"

cd "$REPO_ROOT"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Create output and log directories
mkdir -p "$OUTPUT_DIR"
mkdir -p "$(dirname "$LOG_FILE")"

echo -e "${GREEN}🚀 Batch Q&A Generation (ALL 1000 memes)${NC}" | tee -a "$LOG_FILE"
echo "==========================================" | tee -a "$LOG_FILE"
echo "Output dir: $OUTPUT_DIR" | tee -a "$LOG_FILE"
echo "LLM Provider: $LLM_PROVIDER" | tee -a "$LOG_FILE"
echo "LLM Model: $LLM_MODEL" | tee -a "$LOG_FILE"
echo "Log file: $LOG_FILE" | tee -a "$LOG_FILE"
echo "Progress file: $PROGRESS_FILE" | tee -a "$LOG_FILE"
echo ""

# Generate input list from all available TTL files
echo "📋 Generating input list from all TTL files..." | tee -a "$LOG_FILE"
INPUT_LIST="/tmp/qa_all_images.txt"
cd "$OUTPUT_REVERSED_DIR"
ls *_refined_ontology.ttl 2>/dev/null | sed 's/_refined_ontology.ttl$//' | sort > "$INPUT_LIST"

total=$(wc -l < "$INPUT_LIST")
echo -e "${YELLOW}📊 Total images to process: $total${NC}" | tee -a "$LOG_FILE"
echo ""

if [[ $total -eq 0 ]]; then
    echo -e "${RED}❌ No TTL files found in $OUTPUT_REVERSED_DIR${NC}" | tee -a "$LOG_FILE"
    exit 1
fi

# Process each image
idx=0
success=0
failed=0
skipped=0
total_start_time=$(date +%s)
total_llm_calls=0

echo "Starting processing at $(date)" | tee -a "$LOG_FILE"
echo "==========================================" | tee -a "$LOG_FILE"
echo ""

# Read input file into array to avoid file descriptor conflicts
mapfile -t image_list < "$INPUT_LIST"

for image_name in "${image_list[@]}"; do
    # Skip empty lines
    [[ -z "$image_name" ]] && continue
    
    idx=$((idx + 1))
    
    # Check if already processed (skip if output directory exists with files)
    output_qa_dir="$OUTPUT_DIR/${image_name}_qa"
    if [[ -d "$output_qa_dir" ]]; then
        # Count dimensions to see if it's complete (should have 13 dimensions)
        dimension_dirs=$(find "$output_qa_dir" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l)
        # Also check if there are actual Q&A files (not just empty directories)
        qa_files=$(find "$output_qa_dir" -type f -name "*.jsonld" 2>/dev/null | wc -l)
        if [[ $dimension_dirs -ge 10 ]] && [[ $qa_files -gt 0 ]]; then
            echo -e "${YELLOW}[$idx/$total] Skipping (already processed): $image_name (${dimension_dirs} dimensions, ${qa_files} Q&A files)${NC}" | tee -a "$LOG_FILE"
            skipped=$((skipped + 1))
            continue
        elif [[ $dimension_dirs -gt 0 ]] || [[ $qa_files -gt 0 ]]; then
            echo -e "${YELLOW}[$idx/$total] Incomplete output detected, reprocessing: $image_name (${dimension_dirs} dimensions, ${qa_files} Q&A files)${NC}" | tee -a "$LOG_FILE"
        fi
    fi
    
    meme_start_time=$(date +%s)
    meme_llm_calls=0
    
    echo -e "${BLUE}==========================================${NC}" | tee -a "$LOG_FILE"
    echo -e "${CYAN}[$idx/$total] Processing: $image_name${NC}" | tee -a "$LOG_FILE"
    echo "$(date '+%Y-%m-%d %H:%M:%S') - [$idx/$total] Processing: $image_name" >> "$PROGRESS_FILE"
    echo ""
    
    # Find image file
    image_path=""
    for ext in png jpg jpeg; do
        candidate="$IMG_DIR/${image_name}.${ext}"
        if [[ -f "$candidate" ]]; then
            image_path="$candidate"
            break
        fi
    done
    
    if [[ -z "$image_path" ]]; then
        echo -e "${RED}❌ Image not found for: $image_name${NC}" | tee -a "$LOG_FILE"
        echo "$(date '+%Y-%m-%d %H:%M:%S') - [$idx/$total] FAILED: Image not found for $image_name" >> "$PROGRESS_FILE"
        failed=$((failed + 1))
        continue
    fi
    
    # Check if TTL file exists
    ttl_file="$OUTPUT_REVERSED_DIR/${image_name}_refined_ontology.ttl"
    if [[ ! -f "$ttl_file" ]]; then
        echo -e "${RED}❌ TTL file not found: $ttl_file${NC}" | tee -a "$LOG_FILE"
        echo "$(date '+%Y-%m-%d %H:%M:%S') - [$idx/$total] FAILED: TTL file not found for $image_name" >> "$PROGRESS_FILE"
        failed=$((failed + 1))
        continue
    fi
    
    echo -e "${YELLOW}📄 TTL file: $(basename $ttl_file)${NC}" | tee -a "$LOG_FILE"
    echo -e "${YELLOW}🖼️  Image: $(basename $image_path)${NC}" | tee -a "$LOG_FILE"
    echo ""
    
    # Run Q&A generation
    export HUGGINGFACE_MODEL="$LLM_MODEL"
    if { "$SCRIPT_DIR/run_qa_generation_reversed.sh" \
        --image-path "$image_path" \
        --output-reversed-dir "$OUTPUT_REVERSED_DIR" \
        --output-dir "$OUTPUT_DIR" \
        --llm-provider "$LLM_PROVIDER" \
        --use-ttl \
        --ttl-file "$ttl_file" \
        --questions-per-dimension 1; } >> "$LOG_FILE" 2>&1; then
        
        meme_end_time=$(date +%s)
        meme_duration=$((meme_end_time - meme_start_time))
        
        # Count dimensions processed (approximate from log)
        dimensions_count=$(grep -c "Processing dimension:" "/tmp/qa_${image_name}.log" 2>/dev/null || echo "0")
        # Remove any newlines and ensure it's a number
        dimensions_count=$(echo "$dimensions_count" | tr -d '\n' | grep -oE '[0-9]+' | head -1)
        [[ -z "$dimensions_count" ]] && dimensions_count=0
        meme_llm_calls=$dimensions_count
        total_llm_calls=$((total_llm_calls + meme_llm_calls))
        
        echo ""
        echo -e "${GREEN}✅ Success${NC}" | tee -a "$LOG_FILE"
        echo -e "${CYAN}⏱️  Time: ${meme_duration}s | Dimensions: $dimensions_count | LLM calls: $meme_llm_calls${NC}" | tee -a "$LOG_FILE"
        echo "$(date '+%Y-%m-%d %H:%M:%S') - [$idx/$total] SUCCESS: $image_name (${meme_duration}s, $dimensions_count dimensions)" >> "$PROGRESS_FILE"
        success=$((success + 1))
    else
        meme_end_time=$(date +%s)
        meme_duration=$((meme_end_time - meme_start_time))
        echo ""
        echo -e "${RED}❌ Failed (check log)${NC}" | tee -a "$LOG_FILE"
        echo -e "${CYAN}⏱️  Time: ${meme_duration}s${NC}" | tee -a "$LOG_FILE"
        echo "$(date '+%Y-%m-%d %H:%M:%S') - [$idx/$total] FAILED: $image_name (${meme_duration}s)" >> "$PROGRESS_FILE"
        failed=$((failed + 1))
    fi
    
    echo ""
    
    # Print progress every 10 memes
    if [[ $((idx % 10)) -eq 0 ]]; then
        elapsed=$((meme_end_time - total_start_time))
        avg_time=$((elapsed / idx))
        remaining=$((total - idx))
        estimated_remaining=$((avg_time * remaining))
        estimated_total=$((avg_time * total))
        estimated_completion_time=$((total_start_time + estimated_total))
        estimated_completion_date=$(date -d "@$estimated_completion_time" '+%Y-%m-%d %H:%M:%S' 2>/dev/null || echo "N/A")
        
        echo -e "${YELLOW}📊 Progress: $idx/$total (${success} success, ${failed} failed, ${skipped} skipped)${NC}" | tee -a "$LOG_FILE"
        echo -e "${YELLOW}⏱️  Elapsed: ${elapsed}s ($(($elapsed / 60))m) | Avg: ${avg_time}s/meme${NC}" | tee -a "$LOG_FILE"
        echo -e "${YELLOW}⏱️  Est. remaining: ${estimated_remaining}s ($(($estimated_remaining / 60))m $(($estimated_remaining % 60))s)${NC}" | tee -a "$LOG_FILE"
        echo -e "${YELLOW}⏱️  Est. total time: ${estimated_total}s ($(($estimated_total / 60))m) | Est. completion: ${estimated_completion_date}${NC}" | tee -a "$LOG_FILE"
        echo "" | tee -a "$LOG_FILE"
    fi
    
done

# Ensure we actually processed all files
if [[ $idx -lt $total ]]; then
    echo -e "${RED}⚠️  WARNING: Script stopped early! Processed $idx/$total files${NC}" | tee -a "$LOG_FILE"
    echo "$(date '+%Y-%m-%d %H:%M:%S') - WARNING: Script stopped early at $idx/$total" >> "$PROGRESS_FILE"
fi

# Final summary
total_end_time=$(date +%s)
total_duration=$((total_end_time - total_start_time))
avg_time_per_meme=$((total_duration / total))
estimated_1000=$((avg_time_per_meme * 1000))

echo -e "${GREEN}==========================================${NC}" | tee -a "$LOG_FILE"
echo -e "${GREEN}✅ Successful: $success${NC}" | tee -a "$LOG_FILE"
echo -e "${RED}❌ Failed: $failed${NC}" | tee -a "$LOG_FILE"
echo -e "${YELLOW}⏭️  Skipped (already processed): $skipped${NC}" | tee -a "$LOG_FILE"
echo -e "${YELLOW}📊 Total: $total${NC}" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
echo -e "${CYAN}📈 Statistics:${NC}" | tee -a "$LOG_FILE"
echo -e "   Total time: ${total_duration}s ($(($total_duration / 60))m $(($total_duration % 60))s)" | tee -a "$LOG_FILE"
echo -e "   Avg per meme: ${avg_time_per_meme}s" | tee -a "$LOG_FILE"
echo -e "   Total LLM calls: $total_llm_calls" | tee -a "$LOG_FILE"
echo -e "   Avg LLM calls per meme: $((total_llm_calls / total))" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
echo "Completed at $(date)" | tee -a "$LOG_FILE"
echo "$(date '+%Y-%m-%d %H:%M:%S') - COMPLETED: $success success, $failed failed, ${total_duration}s total" >> "$PROGRESS_FILE"

