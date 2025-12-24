#!/bin/bash

# Batch Q&A Generation Script
# Processes multiple TTL files for Q&A generation

set -e

# Configuration
INPUT_LIST="/tmp/qa_images_to_process.txt"
OUTPUT_REVERSED_DIR="/home/stefano/memes/semantic-memes/output_reversed/hateful-memes-out"
OUTPUT_DIR="/home/stefano/memes/semantic-memes/output_reversed/qa"
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
NC='\033[0m'

echo -e "${GREEN}🚀 Batch Q&A Generation${NC}"
echo "=========================="
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

# Process each image
idx=0
success=0
failed=0

while IFS= read -r image_name; do
    idx=$((idx + 1))
    
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
        echo -e "${RED}[$idx/$total] ❌ Image not found for: $image_name${NC}"
        failed=$((failed + 1))
        continue
    fi
    
    # Check if TTL file exists
    ttl_file="$OUTPUT_REVERSED_DIR/${image_name}_refined_ontology.ttl"
    if [[ ! -f "$ttl_file" ]]; then
        echo -e "${RED}[$idx/$total] ❌ TTL file not found: $ttl_file${NC}"
        failed=$((failed + 1))
        continue
    fi
    
    echo -e "${GREEN}[$idx/$total] 📸 Processing: $image_name${NC}"
    
    # Run Q&A generation
    # Export HuggingFace model for the script
    export HUGGINGFACE_MODEL="$LLM_MODEL"
    if "$SCRIPT_DIR/run_qa_generation_reversed.sh" \
        --image-path "$image_path" \
        --output-reversed-dir "$OUTPUT_REVERSED_DIR" \
        --output-dir "$OUTPUT_DIR" \
        --llm-provider "$LLM_PROVIDER" \
        --use-ttl \
        --ttl-file "$ttl_file" \
        > "/tmp/qa_${image_name}.log" 2>&1; then
        echo -e "${GREEN}  ✅ Success${NC}"
        success=$((success + 1))
    else
        echo -e "${RED}  ❌ Failed (check /tmp/qa_${image_name}.log)${NC}"
        failed=$((failed + 1))
    fi
    
    echo ""
done < "$INPUT_LIST"

# Summary
echo "=========================="
echo -e "${GREEN}✅ Successful: $success${NC}"
echo -e "${RED}❌ Failed: $failed${NC}"
echo -e "${YELLOW}📊 Total: $total${NC}"

