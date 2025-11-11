#!/bin/bash
# Wrapper script for meme pipeline with Core/All mode support

set -e

# Determine repo root (two levels up from scripts/sh)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Meme Pipeline Runner${NC}"
echo "=========================="

# Default configuration
IMAGE_PATH=""
MODE=""
DIMENSIONS=""
LLM_PROVIDER="claude"
OUTPUT_DIR="$REPO_ROOT/output"

# Function to show help
show_help() {
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  --image PATH              Path to meme image (required)"
    echo "  --mode Core|All           Use predefined dimension sets"
    echo "    Core: TextualMaterial, VisualMaterial, Scene, BackgroundKnowledge"
    echo "    All:  All 13 available dimensions"
    echo "  --llm-provider PROVIDER   LLM provider: claude or huggingface (default: claude)"
    echo "  --output-dir DIR          Output directory (default: ./output)"
    echo "  --help                    Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --image 9_image_batch_2.png --mode Core"
    echo "  $0 --image 9_image_batch_2.png --mode All"
    echo "  $0 --image 9_image_batch_2.png --mode Core --llm-provider huggingface"
    echo "  $0 --image 9_image_batch_2.png --mode All --llm-provider huggingface"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --image)
            IMAGE_PATH="$2"
            shift 2
            ;;
        --mode)
            if [[ "$2" == "Core" ]]; then
                DIMENSIONS="TextualMaterial VisualMaterial Scene BackgroundKnowledge"
                echo -e "${BLUE}📊 Using Core dimensions: $DIMENSIONS${NC}"
            elif [[ "$2" == "All" ]]; then
                DIMENSIONS="TextualMaterial VisualMaterial Emotion ColorComposition Scene BackgroundKnowledge Metadata AnalogicalMapping OverallIntent SemioticInterpretation TargetCommunity TemplateStructure Toxicity"
                echo -e "${BLUE}📊 Using All dimensions: $DIMENSIONS${NC}"
            else
                echo -e "${RED}❌ Error: --mode must be either 'Core' or 'All'${NC}"
                exit 1
            fi
            shift 2
            ;;
        --llm-provider)
            LLM_PROVIDER="$2"
            shift 2
            ;;
        --output-dir)
            OUTPUT_DIR="$2"
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
done

# Validate inputs
if [[ -z "$IMAGE_PATH" ]]; then
    echo -e "${RED}❌ Error: --image is required${NC}"
    echo "Use --help for usage information"
    exit 1
fi

if [[ -z "$DIMENSIONS" ]]; then
    echo -e "${RED}❌ Error: --mode is required${NC}"
    echo "Use --help for usage information"
    exit 1
fi

# Resolve bare filenames to $REPO_ROOT/img directory (keep explicit paths working)
if [[ ! -f "$IMAGE_PATH" ]]; then
    BASENAME_ONLY=$(basename -- "$IMAGE_PATH")
    CANDIDATE_PATH="$REPO_ROOT/img/$BASENAME_ONLY"
    if [[ -f "$CANDIDATE_PATH" ]]; then
        IMAGE_PATH="$CANDIDATE_PATH"
    else
        echo -e "${RED}❌ Error: Image file not found: $IMAGE_PATH${NC}"
        echo "Tried also: $CANDIDATE_PATH"
        exit 1
    fi
fi

# Activate environment
echo -e "${BLUE}🐍 Activating conda environment...${NC}"
source ~/miniconda3/etc/profile.d/conda.sh
conda activate meme-qa-pipeline-env

# Set environment variables
export CLAUDE_API_KEY="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"
export ONTOLOGY_PATH="/home/sdegiorgis/memes/meme-pipeline-server/memes-features/meme-dimensions.ttl"
export PROMPTS_DIR="/home/sdegiorgis/memes/meme-pipeline-server/prompts/dimension-extraction-prompts-refined"
export OUTPUT_DIR="$OUTPUT_DIR"

echo -e "${GREEN}🔧 Environment configured${NC}"

# Run the pipeline
echo -e "${BLUE}🚀 Starting meme analysis pipeline...${NC}"
echo "=================================="

python scripts/py/run_pipeline.py "$IMAGE_PATH" \
    --mode dimension_extraction \
    --dimensions $DIMENSIONS \
    --llm-provider "$LLM_PROVIDER" \
    --output-dir "$OUTPUT_DIR"

echo ""
echo -e "${GREEN}🎉 Pipeline completed successfully!${NC}"
echo -e "${YELLOW}📁 Check output files in: $OUTPUT_DIR${NC}"
