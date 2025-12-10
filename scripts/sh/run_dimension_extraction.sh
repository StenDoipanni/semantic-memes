#!/bin/bash

# Meme Analysis Pipeline - Dimension Extraction Script
# This script sets up the environment and runs dimension extraction

echo "🚀 Meme Analysis Pipeline - Dimension Extraction"
echo "================================================"

# Determine repo root (two levels up from scripts/sh)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT"

# Set environment variables
# API key should be set via environment variable or .env file
# Do not hardcode API keys in version control
# export CLAUDE_API_KEY="${CLAUDE_API_KEY:-}"
export ONTOLOGY_PATH="/home/sdegiorgis/memes/meme-pipeline-server/memes-features/meme-dimensions.ttl"
export PROMPTS_DIR="/home/sdegiorgis/memes/meme-pipeline-server/memes-features/prompts/dimension-extraction-prompts"
export OUTPUT_DIR="$REPO_ROOT/output"

echo "📋 Configuration:"
echo "  - Claude API Key: Set"
echo "  - Ontology Path: $ONTOLOGY_PATH"
echo "  - Prompts Dir: $PROMPTS_DIR"
echo "  - Output Dir: $OUTPUT_DIR"
echo ""

# Activate conda environment
echo "🔧 Activating conda environment..."
# Try different conda paths
if [ -f ~/miniconda3/etc/profile.d/conda.sh ]; then
    source ~/miniconda3/etc/profile.d/conda.sh
elif [ -f /opt/miniconda3/etc/profile.d/conda.sh ]; then
    source /opt/miniconda3/etc/profile.d/conda.sh
elif [ -f ~/anaconda3/etc/profile.d/conda.sh ]; then
    source ~/anaconda3/etc/profile.d/conda.sh
else
    echo "⚠️  Conda not found in standard locations, trying direct activation..."
fi

conda activate meme-questions-gen-env

# Check if we're in the right environment
if [[ "$CONDA_DEFAULT_ENV" != "meme-questions-gen-env" ]]; then
    echo "❌ Failed to activate meme-questions-gen-env environment"
    exit 1
fi

echo "✅ Environment activated: $CONDA_DEFAULT_ENV"
echo ""

# Install dependencies if needed
echo "📦 Checking dependencies..."
python -c "import rdflib, anthropic, requests, PIL" 2>/dev/null || {
    echo "Installing missing dependencies..."
    pip install rdflib anthropic requests Pillow python-dotenv pydantic typing-extensions
}

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Default image path (may be overridden). If a bare filename is passed, we will
# resolve it against $REPO_ROOT/img below.
IMAGE_PATH="9_image_batch_2.png"

# Dimension sets
CORE_DIMENSIONS="TextualMaterial VisualMaterial Scene BackgroundKnowledge"
ALL_DIMENSIONS="TextualMaterial VisualMaterial Emotion ColorComposition Scene BackgroundKnowledge Metadata AnalogicalMapping OverallIntent SemioticProjection TargetCommunity TemplateStructure Toxicity"

# Default to Core dimensions
DIMENSIONS="$CORE_DIMENSIONS"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --image)
            IMAGE_PATH="$2"
            shift 2
            ;;
        --mode)
            if [[ "$2" == "Core" ]]; then
                DIMENSIONS="$CORE_DIMENSIONS"
                echo "📊 Using Core dimensions: $DIMENSIONS"
            elif [[ "$2" == "All" ]]; then
                DIMENSIONS="$ALL_DIMENSIONS"
                echo "📊 Using All dimensions: $DIMENSIONS"
            else
                echo "❌ Error: --mode must be either 'Core' or 'All'"
                echo "  Core: $CORE_DIMENSIONS"
                echo "  All:  $ALL_DIMENSIONS"
                exit 1
            fi
            shift 2
            ;;
        --dimensions)
            DIMENSIONS="$2"
            shift 2
            ;;
        --output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --image PATH              Path to meme image (default: $IMAGE_PATH)"
            echo "  --mode Core|All           Use predefined dimension sets"
            echo "    Core: TextualMaterial, VisualMaterial, Scene, BackgroundKnowledge"
            echo "    All:  All 13 available dimensions"
            echo "  --dimensions \"DIM1 DIM2\"  Space-separated list of dimensions (overrides --mode)"
            echo "  --output-dir PATH         Output directory (default: $OUTPUT_DIR)"
            echo "  --help                    Show this help message"
            echo ""
            echo "Available dimensions:"
            echo "  VisualMaterial, TextualMaterial, Emotion, ColorComposition,"
            echo "  Scene, BackgroundKnowledge, Metadata,"
            echo "  AnalogicalMapping, OverallIntent, SemioticProjection,"
            echo "  TargetCommunity, TemplateStructure, Toxicity"
            echo ""
            echo "Examples:"
            echo "  $0 --mode Core                    # Use core dimensions"
            echo "  $0 --mode All                     # Use all dimensions"
            echo "  $0 --dimensions \"VisualMaterial TextualMaterial\"  # Custom dimensions"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo "🎯 Running dimension extraction..."
echo "  - Image: $IMAGE_PATH"
echo "  - Dimensions: $DIMENSIONS"
echo "  - Output: $OUTPUT_DIR"
echo ""

# Resolve bare filenames to $REPO_ROOT/img directory (keep explicit paths working)
if [[ ! -f "$IMAGE_PATH" ]]; then
    BASENAME_ONLY=$(basename -- "$IMAGE_PATH")
    CANDIDATE_PATH="$REPO_ROOT/img/$BASENAME_ONLY"
    if [[ -f "$CANDIDATE_PATH" ]]; then
        IMAGE_PATH="$CANDIDATE_PATH"
    else
        echo "❌ Error: Image file not found: $IMAGE_PATH"
        echo "Tried also: $CANDIDATE_PATH"
        exit 1
    fi
fi

# Run the pipeline
python scripts/py/run_pipeline.py "$IMAGE_PATH" \
    --mode dimension_extraction \
    --dimensions $DIMENSIONS \
    --output-dir "$OUTPUT_DIR" \
    --llm-provider claude

echo ""
echo "✅ Dimension extraction completed!"
echo "📁 Check output files in: $OUTPUT_DIR"
