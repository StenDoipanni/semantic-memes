#!/bin/bash

# Server Pipeline Execution Script
# Optimized for server deployment with local LLMs

set -e  # Exit on any error

# Determine repo root (two levels up from scripts/sh) when running locally,
# but preserve server paths for SERVER_BASE_DIR.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🖥️  Meme Pipeline - Server Mode${NC}"
echo "=================================="

# Server configuration
SERVER_BASE_DIR="/opt/meme-pipeline"
VENV_PATH="$SERVER_BASE_DIR/venv"
OUTPUT_DIR="$SERVER_BASE_DIR/output"

# Default configuration
IMAGE_PATH=""
DIMENSIONS="TextualMaterial VisualMaterial SceneUnderstanding BackgroundKnowledge"
LLM_PROVIDER="ollama"
OLLAMA_MODEL="llama3.2:latest"

# Function to show help
show_help() {
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  --image PATH              Path to meme image (required)"
    echo "  --mode Core|All           Use predefined dimension sets"
    echo "    Core: TextualMaterial, VisualMaterial, SceneUnderstanding, BackgroundKnowledge"
    echo "    All:  All 13 available dimensions"
    echo "  --dimensions \"DIM1 DIM2\"  Space-separated list of dimensions (overrides --mode)"
    echo "  --llm-provider PROVIDER   LLM provider: ollama or claude (default: ollama)"
    echo "  --model MODEL             Ollama model to use (default: llama3.2:latest)"
    echo "  --help                    Show this help message"
    echo ""
    echo "Available Ollama models:"
    echo "  llama3.2:latest, llama3.1:latest, llama3:latest,"
    echo "  mistral:latest, codellama:latest, phi3:latest"
    echo ""
    echo "Examples:"
    echo "  $0 --image /path/to/meme.jpg --mode Core"
    echo "  $0 --image /path/to/meme.jpg --mode All --model mistral:latest"
    echo "  $0 --image /path/to/meme.jpg --dimensions \"TextualMaterial VisualMaterial\""
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
                DIMENSIONS="TextualMaterial VisualMaterial SceneUnderstanding BackgroundKnowledge"
                echo -e "${BLUE}📊 Using Core dimensions: $DIMENSIONS${NC}"
            elif [[ "$2" == "All" ]]; then
                DIMENSIONS="TextualMaterial VisualMaterial EmotionExpression ColorComposition SceneUnderstanding BackgroundKnowledge Metadata MetaphoricalAndAnalogicalMapping OverallIntent SemioticInterpretation TargetCommunity TemplateStructure ToxicityAssessment"
                echo -e "${BLUE}📊 Using All dimensions: $DIMENSIONS${NC}"
            else
                echo -e "${RED}❌ Error: --mode must be either 'Core' or 'All'${NC}"
                exit 1
            fi
            shift 2
            ;;
        --dimensions)
            DIMENSIONS="$2"
            shift 2
            ;;
        --llm-provider)
            LLM_PROVIDER="$2"
            shift 2
            ;;
        --model)
            OLLAMA_MODEL="$2"
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

# Resolve bare filenames to $SERVER_BASE_DIR/img directory on server
if [[ ! -f "$IMAGE_PATH" ]]; then
    BASENAME_ONLY=$(basename -- "$IMAGE_PATH")
    CANDIDATE_PATH="$SERVER_BASE_DIR/img/$BASENAME_ONLY"
    if [[ -f "$CANDIDATE_PATH" ]]; then
        IMAGE_PATH="$CANDIDATE_PATH"
    else
        # Also try local repo img for developer runs
        LOCAL_CANDIDATE_PATH="$REPO_ROOT/img/$BASENAME_ONLY"
        if [[ -f "$LOCAL_CANDIDATE_PATH" ]]; then
            IMAGE_PATH="$LOCAL_CANDIDATE_PATH"
        else
        echo -e "${RED}❌ Error: Image file not found: $IMAGE_PATH${NC}"
        echo "Tried also: $CANDIDATE_PATH"
        exit 1
        fi
    fi
fi

# Check if running on server
if [[ ! -d "$SERVER_BASE_DIR" ]]; then
    echo -e "${RED}❌ Error: Not running on server. Expected directory: $SERVER_BASE_DIR${NC}"
    exit 1
fi

echo -e "${YELLOW}📋 Server Configuration:${NC}"
echo "  Image: $IMAGE_PATH"
echo "  Dimensions: $DIMENSIONS"
echo "  LLM Provider: $LLM_PROVIDER"
if [[ "$LLM_PROVIDER" == "ollama" ]]; then
    echo "  Ollama Model: $OLLAMA_MODEL"
fi
echo "  Output Directory: $OUTPUT_DIR"
echo ""

# Activate virtual environment
echo -e "${BLUE}🐍 Activating Python virtual environment...${NC}"
source "$VENV_PATH/bin/activate"

# Set environment variables
export ONTOLOGY_PATH="$SERVER_BASE_DIR/memes-features/meme-dimensions.ttl"
export PROMPTS_DIR="$SERVER_BASE_DIR/memes-features/prompts/dimension-extraction-prompts"
export OUTPUT_DIR="$OUTPUT_DIR"
export LLM_PROVIDER="$LLM_PROVIDER"

if [[ "$LLM_PROVIDER" == "ollama" ]]; then
    export OLLAMA_MODEL="$OLLAMA_MODEL"
fi

echo -e "${GREEN}🔧 Environment configured${NC}"

# Check Ollama if using local LLM
if [[ "$LLM_PROVIDER" == "ollama" ]]; then
    echo -e "${BLUE}🤖 Checking Ollama service...${NC}"
    if ! curl -s http://localhost:11434/api/tags > /dev/null; then
        echo -e "${RED}❌ Error: Ollama service not running${NC}"
        echo "Please start Ollama: systemctl start ollama"
        exit 1
    fi
    
    # Check if model is available
    if ! ollama list | grep -q "$OLLAMA_MODEL"; then
        echo -e "${YELLOW}⚠️  Model $OLLAMA_MODEL not found. Pulling...${NC}"
        ollama pull "$OLLAMA_MODEL"
    fi
    
    echo -e "${GREEN}✅ Ollama service ready${NC}"
fi

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Run the pipeline
echo -e "${BLUE}🚀 Starting meme analysis pipeline...${NC}"
echo "=================================="

python3 scripts/py/run_pipeline.py "$IMAGE_PATH" \
    --mode dimension_extraction \
    --dimensions $DIMENSIONS \
    --output-dir "$OUTPUT_DIR" \
    --llm-provider "$LLM_PROVIDER"

echo ""
echo -e "${GREEN}🎉 Pipeline completed successfully!${NC}"
echo -e "${YELLOW}📁 Check output files in: $OUTPUT_DIR${NC}"

