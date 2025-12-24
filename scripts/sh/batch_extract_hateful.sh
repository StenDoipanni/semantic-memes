#!/bin/bash

# Batch Hateful Memes Dimension Extraction Pipeline (Bash version - no SLURM)
# Iteratively processes all images in a folder using the extraction script

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Keep strict error checking for setup, but allow processing loop to continue on errors
# set -e is active for setup, we'll handle errors in the processing loop

echo -e "${BLUE}🚀 Batch Hateful Memes Dimension Extraction Pipeline${NC}"
echo "====================================================="
echo ""

# Get the repository root directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT"

# Fix PyTorch import issue with Intel MKL (missing JIT symbols)
if [[ -f "$REPO_ROOT/libijitstub.so" ]]; then
    export LD_PRELOAD="$REPO_ROOT/libijitstub.so:$LD_PRELOAD"
    echo -e "${GREEN}✅ PyTorch fix library loaded${NC}"
fi

# Set GPU environment variables (if GPU is available)
export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"
export HUGGINGFACE_DEVICE="${HUGGINGFACE_DEVICE:-cuda}"

# Set HuggingFace token for authenticated requests
export HUGGINGFACE_TOKEN="${HUGGINGFACE_TOKEN:-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}"
export HF_TOKEN="$HUGGINGFACE_TOKEN"

# Set pipeline environment variables (relative to repo root)
export ONTOLOGY_PATH="${ONTOLOGY_PATH:-$REPO_ROOT/memes-features/meme-dimensions.ttl}"
export PROMPTS_DIR="${PROMPTS_DIR:-$REPO_ROOT/prompts/dimension-extraction-prompts-refined}"

# Default to Qwen3-VL-8B-Instruct
export HUGGINGFACE_MODEL="${HUGGINGFACE_MODEL:-Qwen/Qwen3-VL-8B-Instruct}"

# Verify CUDA is available (optional - only if using huggingface and GPU is expected)
if [[ "${LLM_PROVIDER:-huggingface}" == "huggingface" ]]; then
    echo -e "${BLUE}🔍 Verifying GPU access (HuggingFace provider)...${NC}"
    
    # Try to activate conda environment first to get Python
    if command -v conda &> /dev/null; then
        source "$(conda info --base)/etc/profile.d/conda.sh" 2>/dev/null || true
        if conda env list | grep -q "meme-qa-pipeline-env"; then
            conda activate meme-qa-pipeline-env 2>/dev/null || true
        fi
    fi
    
    # Find Python (prefer conda, then system)
    PYTHON_CMD=""
    if [[ -n "$CONDA_PREFIX" ]] && [[ -f "$CONDA_PREFIX/bin/python" ]]; then
        PYTHON_CMD="$CONDA_PREFIX/bin/python"
    elif command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    fi
    
    if [[ -n "$PYTHON_CMD" ]]; then
        GPU_CHECK=$($PYTHON_CMD -c "
import torch
print(f'CUDA available: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'GPU Device: {torch.cuda.get_device_name(0)}')
    print(f'GPU Count: {torch.cuda.device_count()}')
else:
    print('CUDA not available')
" 2>&1)
        
        if echo "$GPU_CHECK" | grep -q "CUDA available: True"; then
            echo -e "${GREEN}✅ GPU verified and ready${NC}"
            echo "$GPU_CHECK" | grep -E "(GPU Device|GPU Count)"
        else
            echo -e "${YELLOW}⚠️  GPU not available, but continuing (will use CPU if needed)${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  Python not found, skipping GPU check${NC}"
    fi
    echo ""
fi

# Verify Claude API key is set (only if using claude)
if [[ "${LLM_PROVIDER:-huggingface}" == "claude" ]]; then
    if [[ -z "$CLAUDE_API_KEY" ]]; then
        echo -e "${RED}❌ Error: CLAUDE_API_KEY environment variable is not set!${NC}"
        echo " Please set it in your environment or .env file before running."
        echo " Or use --llm-provider huggingface (default) which doesn't require an API key."
        exit 1
    fi
    
    # Check if API key looks valid (starts with sk-ant-)
    if [[ ! "$CLAUDE_API_KEY" =~ ^sk-ant- ]]; then
        echo -e "${YELLOW}⚠️  Warning: CLAUDE_API_KEY does not start with 'sk-ant-'${NC}"
        echo " This might indicate an invalid API key format."
    fi
    
    echo -e "${GREEN}✅ Claude API key is set (length: ${#CLAUDE_API_KEY} characters)${NC}"
    echo " Key preview: ${CLAUDE_API_KEY:0:20}...${CLAUDE_API_KEY: -10}"
    echo ""
else
    echo -e "${BLUE}ℹ️  Using HuggingFace provider (default) - no API key required${NC}"
    echo ""
fi

# Activate conda environment
if command -v conda &> /dev/null; then
    source "$(conda info --base)/etc/profile.d/conda.sh" 2>/dev/null || true
    if conda env list | grep -q "meme-qa-pipeline-env"; then
        echo -e "${BLUE}🔧 Activating conda environment...${NC}"
        conda activate meme-qa-pipeline-env
        echo -e "${GREEN}✅ Environment activated: meme-qa-pipeline-env${NC}"
        echo ""
    else
        echo -e "${YELLOW}⚠️  Conda environment 'meme-qa-pipeline-env' not found${NC}"
        echo " Continuing with system Python..."
        echo ""
    fi
else
    echo -e "${YELLOW}⚠️  Conda not found, using system Python${NC}"
    echo ""
fi

# Parse command line arguments
# Usage: ./batch_extract_hateful.sh [--llm-provider claude|huggingface] [--llm-model MODEL_NAME] [--output-dir DIR] [--input-dir DIR] [--additional-kb <path> ...] [--iterative-kb true|false]

LLM_PROVIDER="${LLM_PROVIDER:-huggingface}"
OUTPUT_DIR="./output_reversed/hateful-memes-out"
ADDITIONAL_KB=()
ITERATIVE_KB="false"
LLM_MODEL="" # Will be set if --llm-model is provided
INPUT_DIR="./img/hateful-memes-img"

# Parse optional arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --llm-provider)
            LLM_PROVIDER="$2"
            shift 2
            ;;
        --llm-model)
            LLM_MODEL="$2"
            # Set HUGGINGFACE_MODEL environment variable if provided
            export HUGGINGFACE_MODEL="$2"
            shift 2
            ;;
        --output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --input-dir)
            INPUT_DIR="$2"
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
        --help)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --llm-provider PROVIDER    LLM provider: claude or huggingface (default: huggingface)"
            echo "  --llm-model MODEL          HuggingFace model name (e.g., Qwen/Qwen3-VL-8B-Instruct)"
            echo "  --output-dir DIR           Output directory (default: ./output_reversed/hateful-memes-out)"
            echo "  --input-dir DIR            Input directory with images (default: ./img/hateful-memes-img)"
            echo "  --additional-kb PATH       Additional knowledge base file (can specify multiple)"
            echo "  --iterative-kb true|false  Attach KB to all prompts (default: false)"
            echo "  --help                     Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0"
            echo "  $0 --llm-provider claude"
            echo "  $0 --llm-model Qwen/Qwen3-VL-30B-A3B-Instruct"
            echo "  $0 --input-dir ./my_images --output-dir ./my_output"
            exit 0
            ;;
        *)
            echo -e "${YELLOW}⚠️  Warning: Unknown argument: $1 (ignored)${NC}"
            shift
            ;;
    esac
done

# Validate input directory
if [[ ! -d "$INPUT_DIR" ]]; then
    echo -e "${RED}❌ Error: Input directory not found: $INPUT_DIR${NC}"
    echo " Please create the directory or specify a different path with --input-dir"
    exit 1
fi

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

# Check disk space before starting
echo -e "${BLUE}💾 Checking disk space...${NC}"
if command -v df &> /dev/null; then
    AVAILABLE_SPACE=$(df -BG "$OUTPUT_DIR" 2>/dev/null | tail -1 | awk '{print $4}' | sed 's/G//' || echo "unknown")
    if [[ "$AVAILABLE_SPACE" != "unknown" ]] && [[ "$AVAILABLE_SPACE" -lt 1 ]]; then
        echo -e "${YELLOW}⚠️  Warning: Low disk space available: ${AVAILABLE_SPACE}GB${NC}"
        echo " This may cause extraction to fail. Consider cleaning up disk space."
    else
        echo -e "${GREEN}✅ Available disk space: ${AVAILABLE_SPACE}GB${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Could not check disk space${NC}"
fi
echo ""

# Validate additional KB files if provided
if [[ ${#ADDITIONAL_KB[@]} -gt 0 ]]; then
    VALIDATED_KB=()
    for kb_file in "${ADDITIONAL_KB[@]}"; do
        # Try absolute path first
        if [[ -f "$kb_file" ]]; then
            VALIDATED_KB+=("$kb_file")
        # Try relative to repo root
        elif [[ -f "$REPO_ROOT/$kb_file" ]]; then
            VALIDATED_KB+=("$REPO_ROOT/$kb_file")
        else
            echo -e "${RED}❌ Error: Additional KB file not found: $kb_file${NC}"
            echo " Tried also: $REPO_ROOT/$kb_file"
            exit 1
        fi
    done
    ADDITIONAL_KB=("${VALIDATED_KB[@]}")
    echo -e "${BLUE}📚 Additional Knowledge Base(s):${NC}"
    for kb_file in "${ADDITIONAL_KB[@]}"; do
        echo " - $kb_file"
    done
    echo " Iterative KB (attach to all prompts): $ITERATIVE_KB"
    echo ""
fi

# Find all image files in input directory
IMAGE_FILES=()
while IFS= read -r -d '' file; do
    IMAGE_FILES+=("$file")
done < <(find "$INPUT_DIR" -type f \( -iname "*.png" -o -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.gif" -o -iname "*.webp" \) -print0 2>/dev/null | sort -z)

TOTAL_IMAGES=${#IMAGE_FILES[@]}

if [[ $TOTAL_IMAGES -eq 0 ]]; then
    echo -e "${YELLOW}⚠️  Warning: No image files found in $INPUT_DIR${NC}"
    echo " Supported formats: .png, .jpg, .jpeg, .gif, .webp"
    echo ""
    echo "💡 Please add image files to the directory:"
    echo " $INPUT_DIR"
    echo ""
    echo " Or specify a different directory with:"
    echo " --input-dir /path/to/your/images"
    echo ""
    echo "📋 Current directory contents:"
    ls -la "$INPUT_DIR" 2>/dev/null || echo " (directory is empty or doesn't exist)"
    echo ""
    echo -e "${GREEN}✅ Script completed (no images to process)${NC}"
    exit 0
fi

echo -e "${BLUE}📊 Configuration:${NC}"
echo " Input Directory: $INPUT_DIR"
echo " Output Directory: $OUTPUT_DIR"
echo " Total Images Found: $TOTAL_IMAGES"
echo " Pipeline: Reversed (starts with OverallIntent)"
echo " Dimensions: OverallIntent → TextualMaterial → VisualMaterial → Scene → BackgroundKnowledge → EmotionExpression → AnalogicalMapping → SemioticProjection → ToxicityAssessment → TargetCommunity"
echo " LLM Provider: ${LLM_PROVIDER:-huggingface} (default - no API key required)"
if [[ "${LLM_PROVIDER:-huggingface}" == "huggingface" ]]; then
    echo " Model: $HUGGINGFACE_MODEL"
    if [[ -n "$LLM_MODEL" ]]; then
        echo " Model (from --llm-model): $LLM_MODEL"
    fi
    echo " Device: $HUGGINGFACE_DEVICE"
    echo " GPU: $CUDA_VISIBLE_DEVICES"
fi
echo ""

# Create progress tracking file
PROGRESS_FILE="$OUTPUT_DIR/.batch_progress_$(date +%Y%m%d_%H%M%S).txt"
touch "$PROGRESS_FILE"
echo -e "${BLUE}📝 Progress will be saved to: $PROGRESS_FILE${NC}"
echo ""

# Function to check if image is already processed
is_processed() {
    local image_path="$1"
    local basename=$(basename -- "$image_path")
    local name_no_ext="${basename%.*}"
    local expected_output="$OUTPUT_DIR/${name_no_ext}_enhanced_ontology_reversed.ttl"
    
    if [[ -f "$expected_output" ]]; then
        # Check if file is not empty and has reasonable size (at least 1KB)
        if [[ -s "$expected_output" ]] && [[ $(stat -f%z "$expected_output" 2>/dev/null || stat -c%s "$expected_output" 2>/dev/null) -gt 1024 ]]; then
            return 0 # Already processed
        fi
    fi
    
    return 1 # Not processed
}

# Function to log progress
log_progress() {
    local status="$1"
    local image_path="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] $status: $image_path" >> "$PROGRESS_FILE"
}

# Process each image
# Disable exit on error for the processing loop - we want to continue even if one image fails
set +e

PROCESSED=0
SKIPPED=0
FAILED=0
FAILED_IMAGES=()

echo -e "${CYAN}🚀 Starting batch extraction...${NC}"
echo "=========================================="
echo ""

for image_path in "${IMAGE_FILES[@]}"; do
    basename=$(basename -- "$image_path")
    name_no_ext="${basename%.*}"
    expected_output="$OUTPUT_DIR/${name_no_ext}_enhanced_ontology_reversed.ttl"
    
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${CYAN}📸 Processing: $basename ($((PROCESSED + SKIPPED + FAILED + 1))/$TOTAL_IMAGES)${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Check if already processed
    if is_processed "$image_path"; then
        echo -e "${YELLOW}⏭️  Skipping (already processed): $basename${NC}"
        echo " Output exists: $expected_output"
        SKIPPED=$((SKIPPED + 1))
        log_progress "SKIPPED" "$image_path"
        continue
    fi
    
    # Build extraction command using the bash script
    EXTRACTION_CMD="./scripts/sh/extract_dimensions_reversed.sh \"$image_path\" --llm-provider \"${LLM_PROVIDER:-huggingface}\" --output-dir \"$OUTPUT_DIR\""
    
    if [[ -n "$LLM_MODEL" ]]; then
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
    
    # Run extraction with error capture
    echo -e "${BLUE}🔄 Running extraction...${NC}"
    echo " Command: $EXTRACTION_CMD"
    log_progress "STARTED" "$image_path"
    
    # Capture both stdout and stderr
    EXTRACTION_OUTPUT=$(eval $EXTRACTION_CMD 2>&1)
    EXTRACTION_EXIT_CODE=$?
    
    if [[ $EXTRACTION_EXIT_CODE -eq 0 ]]; then
        # Verify output was created
        if is_processed "$image_path"; then
            echo -e "${GREEN}✅ Successfully processed: $basename${NC}"
            echo " Output: $expected_output"
            PROCESSED=$((PROCESSED + 1))
            log_progress "SUCCESS" "$image_path"
        else
            echo -e "${YELLOW}⚠️  Warning: Extraction completed but output file not found or too small${NC}"
            echo " Expected: $expected_output"
            echo " Last output: ${EXTRACTION_OUTPUT: -500}" # Show last 500 chars
            FAILED=$((FAILED + 1))
            FAILED_IMAGES+=("$basename")
            log_progress "FAILED" "$image_path (output not found)"
        fi
    else
        echo -e "${RED}❌ Failed to process: $basename${NC}"
        echo " Exit code: $EXTRACTION_EXIT_CODE"
        echo " Error output: ${EXTRACTION_OUTPUT: -1000}" # Show last 1000 chars
        FAILED=$((FAILED + 1))
        FAILED_IMAGES+=("$basename")
        log_progress "FAILED" "$image_path (exit code: $EXTRACTION_EXIT_CODE)"
    fi
    
    # Print summary so far
    echo ""
    echo -e "${BLUE}📊 Progress Summary:${NC}"
    echo " Processed: $PROCESSED"
    echo " Skipped: $SKIPPED"
    echo " Failed: $FAILED"
    echo " Remaining: $((TOTAL_IMAGES - PROCESSED - SKIPPED - FAILED))"
done

# Re-enable exit on error for final summary
set -e

# Final summary
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}🎉 Batch extraction completed!${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${BLUE}📊 Final Summary:${NC}"
echo " Total Images: $TOTAL_IMAGES"
echo -e " ${GREEN}✅ Successfully Processed: $PROCESSED${NC}"
echo -e " ${YELLOW}⏭️  Skipped (already done): $SKIPPED${NC}"
echo -e " ${RED}❌ Failed: $FAILED${NC}"
echo ""
echo "📁 Output Directory: $OUTPUT_DIR"
echo "📝 Progress Log: $PROGRESS_FILE"
echo ""

if [[ $FAILED -gt 0 ]]; then
    echo -e "${YELLOW}⚠️  Failed Images:${NC}"
    for failed_image in "${FAILED_IMAGES[@]}"; do
        echo " - $failed_image"
    done
    echo ""
    echo "💡 Tip: You can re-run this script to retry failed images."
    echo " Already processed images will be automatically skipped."
    echo ""
fi

echo -e "${GREEN}✅ Job completed${NC}"





