#!/bin/bash

# Test Q&A Generation Script - 5 memes with 2 questions per dimension
# Quick test to estimate timing before running full batch

set -e

# Configuration
OUTPUT_REVERSED_DIR="/home/stefano/memes/semantic-memes/output_reversed/hateful-memes-out"
OUTPUT_DIR="/home/stefano/memes/semantic-memes/output_reversed/hateful_memes_out_final"
LLM_PROVIDER="huggingface"
LLM_MODEL="Qwen/Qwen3-VL-8B-Instruct"
IMG_DIR="/home/stefano/memes/semantic-memes/img/hateful-memes-img"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$REPO_ROOT"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${GREEN}🧪 Test Q&A Generation (5 memes, 2 questions/dimension)${NC}"
echo "=========================================="
echo "Output dir: $OUTPUT_DIR"
echo "LLM Provider: $LLM_PROVIDER"
echo "Questions per dimension: 2"
echo ""

# Generate input list from first 5 TTL files
INPUT_LIST="/tmp/qa_test_5_images.txt"
cd "$OUTPUT_REVERSED_DIR"
ls *_refined_ontology.ttl 2>/dev/null | head -5 | sed 's/_refined_ontology.ttl$//' | sort > "$INPUT_LIST"

total=$(wc -l < "$INPUT_LIST")
echo -e "${YELLOW}📊 Testing with $total memes${NC}"
echo ""

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Process each image
idx=0
success=0
failed=0
total_start_time=$(date +%s)
total_llm_calls=0
times=()

while IFS= read -r image_name; do
    idx=$((idx + 1))
    meme_start_time=$(date +%s)
    
    echo -e "${BLUE}==========================================${NC}"
    echo -e "${CYAN}[$idx/$total] Processing: $image_name${NC}"
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
        echo -e "${RED}❌ Image not found for: $image_name${NC}"
        failed=$((failed + 1))
        continue
    fi
    
    # Check if TTL file exists
    ttl_file="$OUTPUT_REVERSED_DIR/${image_name}_refined_ontology.ttl"
    if [[ ! -f "$ttl_file" ]]; then
        echo -e "${RED}❌ TTL file not found: $ttl_file${NC}"
        failed=$((failed + 1))
        continue
    fi
    
    echo -e "${YELLOW}📄 TTL file: $(basename $ttl_file)${NC}"
    echo -e "${YELLOW}🖼️  Image: $(basename $image_path)${NC}"
    echo ""
    
    # Run Q&A generation
    export HUGGINGFACE_MODEL="$LLM_MODEL"
    if "$SCRIPT_DIR/run_qa_generation_reversed.sh" \
        --image-path "$image_path" \
        --output-reversed-dir "$OUTPUT_REVERSED_DIR" \
        --output-dir "$OUTPUT_DIR" \
        --llm-provider "$LLM_PROVIDER" \
        --use-ttl \
        --ttl-file "$ttl_file" \
        --questions-per-dimension 2 2>&1 | tee "/tmp/qa_test_${image_name}.log"; then
        
        meme_end_time=$(date +%s)
        meme_duration=$((meme_end_time - meme_start_time))
        times+=($meme_duration)
        
        # Count dimensions processed
        dimensions_count=$(grep -c "Processing dimension:" "/tmp/qa_test_${image_name}.log" 2>/dev/null || echo "0")
        meme_llm_calls=$dimensions_count
        total_llm_calls=$((total_llm_calls + meme_llm_calls))
        
        echo ""
        echo -e "${GREEN}✅ Success${NC}"
        echo -e "${CYAN}⏱️  Time: ${meme_duration}s | Dimensions: $dimensions_count | LLM calls: $meme_llm_calls${NC}"
        success=$((success + 1))
    else
        meme_end_time=$(date +%s)
        meme_duration=$((meme_end_time - meme_start_time))
        echo ""
        echo -e "${RED}❌ Failed${NC}"
        echo -e "${CYAN}⏱️  Time: ${meme_duration}s${NC}"
        failed=$((failed + 1))
    fi
    
    echo ""
done < "$INPUT_LIST"

# Calculate statistics
total_end_time=$(date +%s)
total_duration=$((total_end_time - total_start_time))

if [[ ${#times[@]} -gt 0 ]]; then
    # Calculate average
    sum=0
    for t in "${times[@]}"; do
        sum=$((sum + t))
    done
    avg_time=$((sum / ${#times[@]}))
    
    # Calculate min and max
    min_time=${times[0]}
    max_time=${times[0]}
    for t in "${times[@]}"; do
        if [[ $t -lt $min_time ]]; then min_time=$t; fi
        if [[ $t -gt $max_time ]]; then max_time=$t; fi
    done
else
    avg_time=0
    min_time=0
    max_time=0
fi

# Estimate for 1000 memes
estimated_1000_avg=$((avg_time * 1000))
estimated_1000_min=$((min_time * 1000))
estimated_1000_max=$((max_time * 1000))

echo -e "${GREEN}==========================================${NC}"
echo -e "${GREEN}✅ Successful: $success${NC}"
echo -e "${RED}❌ Failed: $failed${NC}"
echo -e "${YELLOW}📊 Total: $total${NC}"
echo ""
echo -e "${CYAN}📈 Timing Statistics:${NC}"
echo -e "   Total time: ${total_duration}s ($(($total_duration / 60))m $(($total_duration % 60))s)"
echo -e "   Average per meme: ${avg_time}s"
echo -e "   Min per meme: ${min_time}s"
echo -e "   Max per meme: ${max_time}s"
echo -e "   Total LLM calls: $total_llm_calls"
echo -e "   Avg LLM calls per meme: $((total_llm_calls / total))"
echo ""
echo -e "${YELLOW}⏱️  Estimated time for 1000 memes:${NC}"
echo -e "   Average estimate: ${estimated_1000_avg}s ($(($estimated_1000_avg / 60))m $(($estimated_1000_avg % 60))s)"
echo -e "   Best case (min): ${estimated_1000_min}s ($(($estimated_1000_min / 60))m $(($estimated_1000_min % 60))s)"
echo -e "   Worst case (max): ${estimated_1000_max}s ($(($estimated_1000_max / 60))m $(($estimated_1000_max % 60))s)"
echo -e "   Hours: $(($estimated_1000_avg / 3600))h $((($estimated_1000_avg % 3600) / 60))m"
echo ""

