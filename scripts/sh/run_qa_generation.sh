#!/bin/bash

# Q&A Generation Pipeline Script
# This script generates Q&A pairs from extracted meme dimensions

set -e  # Exit on any error

# Default configuration
IMAGE_PATH="9_image_batch_2.png"
DIMENSIONS_DIR="./output/dimensions"
OUTPUT_DIR="./output/qa"
LLM_PROVIDER="claude"
CONDA_ENV="meme-qa-pipeline-env"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Q&A Generation Pipeline${NC}"
echo "=================================="

# Set environment variables first
export CLAUDE_API_KEY="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"
export ONTOLOGY_PATH="/home/sdegiorgis/memes/meme-pipeline-server/memes-features/meme-dimensions.ttl"
export PROMPTS_DIR="/home/sdegiorgis/memes/meme-pipeline-server/prompts/dimension-extraction-prompts"

echo -e "${GREEN}🔧 Environment variables set${NC}"

# Function to show help
show_help() {
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  --image PATH              Path to meme image (default: $IMAGE_PATH)"
    echo "  --dimensions-dir PATH     Directory containing dimension folders (default: $DIMENSIONS_DIR)"
    echo "  --output-dir PATH         Output directory for Q&A files (default: $OUTPUT_DIR)"
    echo "  --llm-provider PROVIDER   LLM provider: claude or ollama (default: $LLM_PROVIDER)"
    echo "  --help                    Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                                    # Use default settings"
    echo "  $0 --image /path/to/meme.jpg         # Specify custom image"
    echo "  $0 --llm-provider ollama             # Use Ollama instead of Claude"
    echo "  $0 --dimensions-dir ./custom/dims    # Use custom dimensions directory"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --image)
            IMAGE_PATH="$2"
            shift 2
            ;;
        --dimensions-dir)
            DIMENSIONS_DIR="$2"
            shift 2
            ;;
        --output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --llm-provider)
            LLM_PROVIDER="$2"
            shift 2
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            echo -e "${RED}❌ Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
    shift
done

# Validate inputs
if [[ ! -f "$IMAGE_PATH" ]]; then
    echo -e "${RED}❌ Error: Image file not found: $IMAGE_PATH${NC}"
    exit 1
fi

if [[ ! -d "$DIMENSIONS_DIR" ]]; then
    echo -e "${RED}❌ Error: Dimensions directory not found: $DIMENSIONS_DIR${NC}"
    exit 1
fi

if [[ "$LLM_PROVIDER" != "claude" && "$LLM_PROVIDER" != "ollama" ]]; then
    echo -e "${RED}❌ Error: LLM provider must be 'claude' or 'ollama'${NC}"
    exit 1
fi

# Display configuration
echo -e "${YELLOW}📋 Configuration:${NC}"
echo "  Image: $IMAGE_PATH"
echo "  Dimensions Directory: $DIMENSIONS_DIR"
echo "  Output Directory: $OUTPUT_DIR"
echo "  LLM Provider: $LLM_PROVIDER"
echo "  Conda Environment: $CONDA_ENV"
echo ""

# Activate conda environment
echo -e "${BLUE}🔧 Activating conda environment...${NC}"
# Try different conda paths
if [ -f ~/miniconda3/etc/profile.d/conda.sh ]; then
    source ~/miniconda3/etc/profile.d/conda.sh
elif [ -f /opt/miniconda3/etc/profile.d/conda.sh ]; then
    source /opt/miniconda3/etc/profile.d/conda.sh
elif [ -f ~/anaconda3/etc/profile.d/conda.sh ]; then
    source ~/anaconda3/etc/profile.d/conda.sh
else
    echo -e "${YELLOW}⚠️  Conda not found in standard locations, trying direct activation...${NC}"
fi

conda activate "$CONDA_ENV"

# Check if we're in the right environment
if [[ "$CONDA_DEFAULT_ENV" != "$CONDA_ENV" ]]; then
    echo -e "${RED}❌ Failed to activate $CONDA_ENV environment${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Environment activated: $CONDA_DEFAULT_ENV${NC}"

# Environment variables already set at the beginning of the script

# Create output directory
mkdir -p "$OUTPUT_DIR"
echo -e "${GREEN}📁 Output directory created: $OUTPUT_DIR${NC}"

# Check if dimensions exist
DIMENSION_COUNT=$(find "$DIMENSIONS_DIR" -maxdepth 1 -type d | wc -l)
DIMENSION_COUNT=$((DIMENSION_COUNT - 1))  # Subtract 1 for the directory itself

if [[ $DIMENSION_COUNT -eq 0 ]]; then
    echo -e "${RED}❌ Error: No dimension folders found in $DIMENSIONS_DIR${NC}"
    echo "Please run dimension extraction first"
    exit 1
fi

echo -e "${GREEN}📊 Found $DIMENSION_COUNT dimension folders${NC}"

# List available dimensions
echo -e "${YELLOW}📋 Available dimensions:${NC}"
for dim_dir in "$DIMENSIONS_DIR"/*; do
    if [[ -d "$dim_dir" ]]; then
        dim_name=$(basename "$dim_dir")
        file_count=$(find "$dim_dir" -name "*.jsonld" | wc -l)
        echo "  - $dim_name ($file_count files)"
    fi
done
echo ""

# Run Q&A generation
echo -e "${BLUE}🚀 Starting Q&A generation...${NC}"
echo "=================================="

python3 -c "
import sys
from pathlib import Path
from qa_generation_module import generate_qa_for_image

# Configuration
image_path = Path('$IMAGE_PATH')
dimensions_dir = Path('$DIMENSIONS_DIR')
output_dir = Path('$OUTPUT_DIR')
llm_provider = '$LLM_PROVIDER'

print(f'🖼️  Processing image: {image_path.name}')
print(f'📊 Dimensions directory: {dimensions_dir}')
print(f'💾 Output directory: {output_dir}')
print(f'🤖 LLM Provider: {llm_provider}')
print('')

try:
    result = generate_qa_for_image(
        image_path=image_path,
        dimensions_dir=dimensions_dir,
        output_dir=output_dir,
        llm_provider=llm_provider
    )
    
    if result['success']:
        print(f'✅ Q&A generation completed successfully!')
        print(f'📊 Dimensions processed: {len(result[\"dimensions_processed\"])}')
        print(f'❓ Total Q&A pairs generated: {result[\"total_qa_pairs\"]}')
        
        if result['dimensions_processed']:
            print(f'\\n📋 Processed dimensions:')
            for dim in result['dimensions_processed']:
                print(f'  - {dim}')
        
        if result['errors']:
            print(f'\\n⚠️  Errors encountered:')
            for error in result['errors']:
                print(f'  - {error}')
    else:
        print(f'❌ Q&A generation failed: {result.get(\"error\", \"Unknown error\")}')
        sys.exit(1)
        
except Exception as e:
    print(f'❌ Error running Q&A generation: {e}')
    sys.exit(1)
"

# Check if the Python script succeeded
if [[ $? -eq 0 ]]; then
    echo ""
    echo -e "${GREEN}🎉 Q&A generation pipeline completed successfully!${NC}"
    echo ""
    echo -e "${YELLOW}📁 Output files saved to: $OUTPUT_DIR${NC}"
    echo ""
    echo -e "${BLUE}📋 Generated files:${NC}"
    find "$OUTPUT_DIR" -name "*.jsonld" -o -name "*.txt" | head -10
    if [[ $(find "$OUTPUT_DIR" -name "*.jsonld" -o -name "*.txt" | wc -l) -gt 10 ]]; then
        echo "  ... and more files"
    fi
else
    echo ""
    echo -e "${RED}❌ Q&A generation pipeline failed!${NC}"
    exit 1
fi
