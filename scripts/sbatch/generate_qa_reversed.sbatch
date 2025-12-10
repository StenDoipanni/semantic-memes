#!/bin/bash
#SBATCH --job-name=generate_qa_reversed
#SBATCH --output=logs/slurm/generate_qa_reversed_%j.out
#SBATCH --error=logs/slurm/generate_qa_reversed_%j.err
#SBATCH --partition=gpu_a100
#SBATCH --gpus=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=02:00:00

set -e

echo "🚀 Q&A Generation Pipeline (Reversed)"
echo "====================================="
echo "Job ID: $SLURM_JOB_ID"
echo "Node: $SLURM_NODELIST"
echo "📄 Output file: generate_qa_reversed_${SLURM_JOB_ID}.out (in submission directory)"
echo "📄 Error file: generate_qa_reversed_${SLURM_JOB_ID}.err (in submission directory)"
echo ""

# Load necessary modules
module load 2023
module load Python/3.11.3-GCCcore-12.3.0

# Set pipeline environment variables
# API key should be set via environment variable or .env file
# Do not hardcode API keys in version control
# export CLAUDE_API_KEY="${CLAUDE_API_KEY:-}"
export ONTOLOGY_PATH="/home/sdegiorgis/memes/meme-pipeline-server/memes-features/meme-dimensions.ttl"
export PROMPTS_DIR="/home/sdegiorgis/memes/meme-pipeline-server/prompts/dimension-extraction-prompts-refined"

# Activate conda environment
source /home/sdegiorgis/miniconda3/etc/profile.d/conda.sh
conda activate meme-qa-pipeline-env

# Navigate to pipeline directory
cd /home/sdegiorgis/memes/meme-pipeline-server

# Parse command line arguments
# Usage: sbatch generate_qa_reversed.sbatch <image_name> [--dimensions LIST] [--individuals SPEC] [--use-ttl] [--llm-provider claude|huggingface] [--output-dir PATH]
# Example: sbatch generate_qa_reversed.sbatch sea_monkeys
# Example: sbatch generate_qa_reversed.sbatch sea_monkeys --dimensions OverallIntent,Scene,EmotionExpression
# Example: sbatch generate_qa_reversed.sbatch sea_monkeys --individuals EmotionExpression:amusement,joy
# Example: sbatch generate_qa_reversed.sbatch sea_monkeys --use-ttl

IMAGE_NAME="${1}"
if [[ -z "$IMAGE_NAME" ]]; then
    echo "❌ Error: Image name is required"
    echo ""
    echo "Usage: sbatch generate_qa_reversed.sbatch <image_name> [options]"
    echo ""
    echo "Options:"
    echo "  --dimensions LIST          Comma-separated list of dimensions to process"
    echo "                             Example: OverallIntent,Scene,EmotionExpression"
    echo "  --individuals SPEC          Comma-separated list of specific individuals"
    echo "                             Format: DimensionName:instance1,instance2"
    echo "                             Example: EmotionExpression:amusement,joy"
    echo "  --use-ttl                   Use TTL file instead of JSON-LD files"
    echo "  --llm-provider PROVIDER     LLM provider: claude or huggingface (default: claude)"
    echo "  --output-dir PATH            Output directory (default: ./output_reversed/qa)"
    echo ""
    echo "Examples:"
    echo "  sbatch generate_qa_reversed.sbatch sea_monkeys"
    echo "  sbatch generate_qa_reversed.sbatch sea_monkeys --dimensions OverallIntent,Scene"
    echo "  sbatch generate_qa_reversed.sbatch sea_monkeys --individuals EmotionExpression:amusement,joy"
    echo "  sbatch generate_qa_reversed.sbatch sea_monkeys --use-ttl"
    exit 1
fi

# Parse optional arguments
OUTPUT_REVERSED_DIR="${OUTPUT_REVERSED_DIR:-./output_reversed}"
OUTPUT_DIR="${OUTPUT_DIR:-./output_reversed/qa}"
LLM_PROVIDER="${LLM_PROVIDER:-claude}"
DIMENSIONS=""
INDIVIDUALS=""
USE_TTL="false"
shift

while [[ $# -gt 0 ]]; do
    case $1 in
        --dimensions)
            DIMENSIONS="$2"
            shift 2
            ;;
        --individuals)
            INDIVIDUALS="$2"
            shift 2
            ;;
        --use-ttl)
            USE_TTL="true"
            shift
            ;;
        --llm-provider)
            LLM_PROVIDER="$2"
            shift 2
            ;;
        --output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --output-reversed-dir)
            OUTPUT_REVERSED_DIR="$2"
            shift 2
            ;;
        *)
            echo "⚠️  Warning: Unknown argument: $1 (ignored)"
            shift
            ;;
    esac
done

# Validate LLM provider
if [[ "$LLM_PROVIDER" != "claude" && "$LLM_PROVIDER" != "huggingface" ]]; then
    echo "❌ Error: LLM provider must be 'claude' or 'huggingface'"
    exit 1
fi

# Verify Claude API key is set (if using claude)
if [[ "$LLM_PROVIDER" == "claude" ]]; then
    if [[ -z "$CLAUDE_API_KEY" ]]; then
        echo "❌ Error: CLAUDE_API_KEY environment variable is not set!"
        exit 1
    fi
    echo "✅ Claude API key is set"
    echo ""
fi

# Check if output_reversed directory exists
if [[ ! -d "$OUTPUT_REVERSED_DIR" ]]; then
    echo "❌ Error: Output reversed directory not found: $OUTPUT_REVERSED_DIR"
    echo "   Please run reversed dimension extraction first"
    exit 1
fi

DIMENSIONS_DIR="$OUTPUT_REVERSED_DIR/dimensions"
if [[ ! -d "$DIMENSIONS_DIR" ]]; then
    echo "❌ Error: Dimensions directory not found: $DIMENSIONS_DIR"
    echo "   Please run reversed dimension extraction first"
    exit 1
fi

echo "📊 Configuration:"
echo "  Image Name: $IMAGE_NAME"
echo "  Output Reversed Directory: $OUTPUT_REVERSED_DIR"
echo "  Dimensions Directory: $DIMENSIONS_DIR"
echo "  Output Directory: $OUTPUT_DIR"
echo "  LLM Provider: $LLM_PROVIDER"
if [[ -n "$DIMENSIONS" ]]; then
    echo "  Dimensions to Process: $DIMENSIONS"
fi
if [[ -n "$INDIVIDUALS" ]]; then
    echo "  Specific Individuals: $INDIVIDUALS"
fi
if [[ "$USE_TTL" == "true" ]]; then
    echo "  Using TTL file: Yes"
fi
echo ""

# Run Q&A generation
echo "🚀 Running Q&A generation..."
echo "=================================="

# Build command arguments
CMD_ARGS="--image-name \"$IMAGE_NAME\" --output-reversed-dir \"$OUTPUT_REVERSED_DIR\" --output-dir \"$OUTPUT_DIR\" --llm-provider \"$LLM_PROVIDER\""

if [[ -n "$DIMENSIONS" ]]; then
    CMD_ARGS="$CMD_ARGS --dimensions \"$DIMENSIONS\""
fi

if [[ -n "$INDIVIDUALS" ]]; then
    CMD_ARGS="$CMD_ARGS --individuals \"$INDIVIDUALS\""
fi

if [[ "$USE_TTL" == "true" ]]; then
    CMD_ARGS="$CMD_ARGS --use-ttl"
fi

bash scripts/sh/run_qa_generation_reversed.sh $CMD_ARGS

echo ""
echo "🎉 Q&A generation completed successfully!"
echo "📁 Check output files in: $OUTPUT_DIR"
echo "✅ Job completed"


