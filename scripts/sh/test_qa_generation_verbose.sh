#!/bin/bash

# Test Q&A Generation Script with Verbose Output
# Processes 10 TTL files for Q&A generation with detailed monitoring

set -e

# Configuration
INPUT_LIST="/tmp/qa_test_10_images.txt"
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

echo -e "${GREEN}🚀 Test Q&A Generation (10 memes)${NC}"
echo "=========================================="
echo "Input list: $INPUT_LIST"
echo "Output dir: $OUTPUT_DIR"
echo "LLM Provider: $LLM_PROVIDER"
echo "LLM Model: $LLM_MODEL"
echo ""

# Check if input list exists
if [[ ! -f "$INPUT_LIST" ]]; then
    echo -e "${RED}❌ Error: Input list not found: $INPUT_LIST${NC}"
    exit 1
fi

total=$(wc -l < "$INPUT_LIST")
echo -e "${YELLOW}📊 Total images to process: $total${NC}"
echo ""

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Process each image
idx=0
success=0
failed=0
total_start_time=$(date +%s)
total_llm_calls=0

while IFS= read -r image_name; do
    idx=$((idx + 1))
    meme_start_time=$(date +%s)
    meme_llm_calls=0
    
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
        --ttl-file "$ttl_file" 2>&1 | tee "/tmp/qa_${image_name}.log"; then
        
        meme_end_time=$(date +%s)
        meme_duration=$((meme_end_time - meme_start_time))
        
        # Count dimensions processed (approximate from log)
        dimensions_count=$(grep -c "Processing dimension:" "/tmp/qa_${image_name}.log" 2>/dev/null || echo "0")
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
        echo -e "${RED}❌ Failed (check /tmp/qa_${image_name}.log)${NC}"
        echo -e "${CYAN}⏱️  Time: ${meme_duration}s${NC}"
        failed=$((failed + 1))
    fi
    
    echo ""
done < "$INPUT_LIST"

# Final summary
total_end_time=$(date +%s)
total_duration=$((total_end_time - total_start_time))
avg_time_per_meme=$((total_duration / total))
estimated_1000=$((avg_time_per_meme * 1000))

echo -e "${GREEN}==========================================${NC}"
echo -e "${GREEN}✅ Successful: $success${NC}"
echo -e "${RED}❌ Failed: $failed${NC}"
echo -e "${YELLOW}📊 Total: $total${NC}"
echo ""
echo -e "${CYAN}📈 Statistics:${NC}"
echo -e "   Total time: ${total_duration}s ($(($total_duration / 60))m $(($total_duration % 60))s)"
echo -e "   Avg per meme: ${avg_time_per_meme}s"
echo -e "   Total LLM calls: $total_llm_calls"
echo -e "   Avg LLM calls per meme: $((total_llm_calls / total))"
echo ""
echo -e "${YELLOW}⏱️  Estimated time for 1000 memes:${NC}"
echo -e "   ${estimated_1000}s ($(($estimated_1000 / 60))m $(($estimated_1000 % 60))s)"
echo -e "   ($(($estimated_1000 / 3600))h $((($estimated_1000 % 3600) / 60))m)"
echo ""