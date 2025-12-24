#!/bin/bash

# Batch Processing Script for Dimension Extraction and QA Generation
# Processes all images in a folder, running extraction and QA generation for each

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Batch Dimension Extraction and QA Generation${NC}"
echo "======================================================"
echo ""

# Get the repository root directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT"

# Default configuration
IMAGE_FOLDER=""
OUTPUT_DIR="./output_reversed"
LLM_PROVIDER="huggingface"
LLM_MODEL="Qwen/Qwen3-VL-8B-Instruct"
ADDITIONAL_KB=()
ITERATIVE_KB="false"
SKIP_EXISTING=false

# Function to show help
show_help() {
    echo "Usage: $0 [options] <image_folder>"
    echo ""
    echo "Arguments:"
    echo "  <image_folder>              Folder containing images to process"
    echo ""
    echo "Options:"
    echo "  --output-dir PATH           Output directory (default: ./output_reversed)"
    echo "  --llm-provider PROVIDER    LLM provider: claude or huggingface (default: huggingface)"
    echo "  --llm-model MODEL           HuggingFace model name (default: Qwen/Qwen3-VL-8B-Instruct)"
    echo "  --additional-kb PATH        Additional knowledge base file (can specify multiple)"
    echo "  --iterative-kb true|false   Attach KB to all prompts (default: false)"
    echo "  --skip-existing             Skip images that already have output files"
    echo "  --help                      Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 hateful-memes-img"
    echo "  $0 hateful-memes-img --llm-provider huggingface --llm-model Qwen/Qwen3-VL-8B-Instruct"
    echo "  $0 hateful-memes-img --additional-kb prompts/dimension-extraction-prompts-refined/AdditionalKnowledgeBase.jsonld"
    echo "  $0 hateful-memes-img --skip-existing"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --llm-provider)
            LLM_PROVIDER="$2"
            shift 2
            ;;
        --llm-model)
            LLM_MODEL="$2"
            shift 2
            ;;
        --additional-kb)
            ADDITIONAL_KB+=("$2")
            shift 2
            ;;
        --iterative-kb)
            ITERATIVE_KB="$2"
            shift 2
            ;;
        --skip-existing)
            SKIP_EXISTING=true
            shift
            ;;
        --help)
            show_help
            exit 0
            ;;
        -*)
            echo -e "${RED}❌ Unknown option: $1${NC}"
            show_help
            exit 1
            ;;
        *)
            if [[ -z "$IMAGE_FOLDER" ]]; then
                IMAGE_FOLDER="$1"
            else
                echo -e "${RED}❌ Multiple image folders specified. Please specify only one.${NC}"
                exit 1
            fi
            shift
            ;;
    esac
done

# Check if image folder is provided
if [[ -z "$IMAGE_FOLDER" ]]; then
    echo -e "${RED}❌ Error: Image folder is required${NC}"
    echo ""
    show_help
    exit 1
fi

# Resolve image folder path
if [[ ! "$IMAGE_FOLDER" = /* ]]; then
    # Relative path
    IMAGE_FOLDER="$REPO_ROOT/$IMAGE_FOLDER"
fi

# Check if folder exists
if [[ ! -d "$IMAGE_FOLDER" ]]; then
    echo -e "${RED}❌ Error: Image folder not found: $IMAGE_FOLDER${NC}"
    exit 1
fi

echo -e "${CYAN}📁 Image folder: $IMAGE_FOLDER${NC}"
echo -e "${CYAN}📁 Output directory: $OUTPUT_DIR${NC}"
echo -e "${CYAN}🤖 LLM Provider: $LLM_PROVIDER${NC}"
if [[ "$LLM_PROVIDER" == "huggingface" ]]; then
    echo -e "${CYAN}🤖 LLM Model: $LLM_MODEL${NC}"
fi
if [[ ${#ADDITIONAL_KB[@]} -gt 0 ]]; then
    echo -e "${CYAN}📚 Additional KB files: ${#ADDITIONAL_KB[@]}${NC}"
fi
echo ""

# Find all image files
IMAGE_FILES=()
while IFS= read -r -d '' file; do
    IMAGE_FILES+=("$file")
done < <(find "$IMAGE_FOLDER" -type f \( -iname "*.png" -o -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.gif" -o -iname "*.webp" \) -print0 | sort -z)

if [[ ${#IMAGE_FILES[@]} -eq 0 ]]; then
    echo -e "${YELLOW}⚠️  No image files found in $IMAGE_FOLDER${NC}"
    exit 0
fi

echo -e "${GREEN}✅ Found ${#IMAGE_FILES[@]} image file(s)${NC}"
echo ""

# Process each image
SUCCESS_COUNT=0
FAILED_COUNT=0
SKIPPED_COUNT=0
FAILED_IMAGES=()

for image_file in "${IMAGE_FILES[@]}"; do
    # Get base name without extension
    image_basename=$(basename -- "$image_file")
    image_name="${image_basename%.*}"
    
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}📸 Processing: $image_basename${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    
    # Check if output already exists (if skip-existing is enabled)
    if [[ "$SKIP_EXISTING" == "true" ]]; then
        TTL_FILE="$OUTPUT_DIR/${image_name}_enhanced_ontology_reversed.ttl"
        if [[ -f "$TTL_FILE" ]]; then
            echo -e "${YELLOW}⏭️  Skipping $image_basename (output already exists)${NC}"
            echo ""
            ((SKIPPED_COUNT++))
            continue
        fi
    fi
    
    # Step 1: Dimension Extraction
    echo -e "${CYAN}📊 Step 1/2: Extracting dimensions...${NC}"
    EXTRACTION_CMD="./scripts/sh/extract_dimensions_reversed.sh \"$image_file\" --llm-provider \"$LLM_PROVIDER\" --output-dir \"$OUTPUT_DIR\""
    
    if [[ "$LLM_PROVIDER" == "huggingface" && -n "$LLM_MODEL" ]]; then
        EXTRACTION_CMD="$EXTRACTION_CMD --llm-model \"$LLM_MODEL\""
    fi
    
    if [[ ${#ADDITIONAL_KB[@]} -gt 0 ]]; then
        for kb_file in "${ADDITIONAL_KB[@]}"; do
            EXTRACTION_CMD="$EXTRACTION_CMD --additional-kb \"$kb_file\""
        done
        if [[ "$ITERATIVE_KB" == "true" ]]; then
            EXTRACTION_CMD="$EXTRACTION_CMD --iterative-kb true"
        fi
    fi
    
    if eval $EXTRACTION_CMD; then
        echo -e "${GREEN}✅ Dimension extraction completed for $image_basename${NC}"
        echo ""
    else
        echo -e "${RED}❌ Dimension extraction failed for $image_basename${NC}"
        echo ""
        ((FAILED_COUNT++))
        FAILED_IMAGES+=("$image_basename")
        continue
    fi
    
    # Step 2: QA Generation
    echo -e "${CYAN}❓ Step 2/2: Generating Q&A pairs...${NC}"
    QA_CMD="./scripts/sh/run_qa_generation_reversed.sh --image-path \"$image_file\" --output-reversed-dir \"$OUTPUT_DIR\" --output-dir \"$OUTPUT_DIR/qa\" --llm-provider \"$LLM_PROVIDER\" --use-ttl"
    
    if eval $QA_CMD; then
        echo -e "${GREEN}✅ QA generation completed for $image_basename${NC}"
        echo ""
        ((SUCCESS_COUNT++))
    else
        echo -e "${RED}❌ QA generation failed for $image_basename${NC}"
        echo ""
        ((FAILED_COUNT++))
        FAILED_IMAGES+=("$image_basename")
    fi
    
    echo ""
done

# Summary
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}📊 Batch Processing Summary${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ Successfully processed: $SUCCESS_COUNT${NC}"
if [[ $SKIPPED_COUNT -gt 0 ]]; then
    echo -e "${YELLOW}⏭️  Skipped: $SKIPPED_COUNT${NC}"
fi
if [[ $FAILED_COUNT -gt 0 ]]; then
    echo -e "${RED}❌ Failed: $FAILED_COUNT${NC}"
    echo -e "${RED}Failed images:${NC}"
    for img in "${FAILED_IMAGES[@]}"; do
        echo -e "${RED}  - $img${NC}"
    done
fi
echo ""

if [[ $FAILED_COUNT -eq 0 ]]; then
    echo -e "${GREEN}🎉 All images processed successfully!${NC}"
    exit 0
else
    echo -e "${YELLOW}⚠️  Some images failed to process. Check the errors above.${NC}"
    exit 1
fi







