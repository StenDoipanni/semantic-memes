#!/bin/bash
#SBATCH --job-name=generate_qa
#SBATCH --output=logs/slurm/generate_qa_%j.out
#SBATCH --error=logs/slurm/generate_qa_%j.err
#SBATCH --partition=gpu_a100
#SBATCH --gpus=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=02:00:00

set -e

echo "🚀 Q&A Generation Pipeline"
echo "================================="
echo "Job ID: $SLURM_JOB_ID"
echo "Node: $SLURM_NODELIST"
echo "📄 Output file: generate_qa_${SLURM_JOB_ID}.out (in submission directory)"
echo "📄 Error file: generate_qa_${SLURM_JOB_ID}.err (in submission directory)"
echo ""

# Load necessary modules
module load 2023
module load Python/3.11.3-GCCcore-12.3.0

# Set pipeline environment variables
# API key should be set via environment variable or .env file
# Do not hardcode API keys in version control
# export CLAUDE_API_KEY="${CLAUDE_API_KEY:-}"
export ONTOLOGY_PATH="/home/sdegiorgis/memes/meme-pipeline-server/memes-features/meme-dimensions.ttl"
export PROMPTS_DIR="/home/sdegiorgis/memes/meme-pipeline-server/prompts/dimension-extraction-prompts"

# Activate conda environment
source /home/sdegiorgis/miniconda3/etc/profile.d/conda.sh
conda activate meme-qa-pipeline-env

# Navigate to pipeline directory
cd /home/sdegiorgis/memes/meme-pipeline-server

# Parse command line arguments
# Usage: sbatch generate_qa.sbatch [image_path] [--dimensions-dir PATH] [--output-dir PATH] [--llm-provider claude|ollama]
# Example: sbatch generate_qa.sbatch img/sea_monkeys.png

IMAGE_PATH="${1:-img/sea_monkeys.png}"
DIMENSIONS_DIR="${DIMENSIONS_DIR:-./output/dimensions}"
OUTPUT_DIR="${OUTPUT_DIR:-./output/qa}"
LLM_PROVIDER="${LLM_PROVIDER:-claude}"

shift

# Parse additional arguments
while [[ $# -gt 0 ]]; do
    case $1 in
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
        *)
            echo "⚠️  Unknown option: $1 (ignoring)"
            shift
            ;;
    esac
done

# Resolve bare filenames to ./img directory (keep explicit paths working)
if [[ ! -f "$IMAGE_PATH" ]]; then
    BASENAME_ONLY=$(basename -- "$IMAGE_PATH")
    CANDIDATE_PATH="./img/$BASENAME_ONLY"
    if [[ -f "$CANDIDATE_PATH" ]]; then
        IMAGE_PATH="$CANDIDATE_PATH"
        echo "📁 Found image at: $IMAGE_PATH"
    else
        echo "❌ Error: Image file not found: $IMAGE_PATH"
        echo "   Tried also: $CANDIDATE_PATH"
        echo ""
        echo "💡 Tip: Make sure the image path is correct."
        echo "   You can use:"
        echo "   - Full path: /path/to/image.png"
        echo "   - Relative path: ./img/image.png"
        echo "   - Filename only: image.png (will look in ./img/)"
        exit 1
    fi
else
    echo "📁 Image found at: $IMAGE_PATH"
fi

echo "📊 Configuration:"
echo "  Image: $IMAGE_PATH"
echo "  Dimensions Directory: $DIMENSIONS_DIR"
echo "  Output Directory: $OUTPUT_DIR"
echo "  LLM Provider: $LLM_PROVIDER"
echo ""

# Run Q&A generation
echo "🚀 Running Q&A generation..."
echo "=================================="
bash scripts/sh/run_qa_generation.sh \
    --image "${IMAGE_PATH}" \
    --dimensions-dir "${DIMENSIONS_DIR}" \
    --output-dir "${OUTPUT_DIR}" \
    --llm-provider "${LLM_PROVIDER}"

echo ""
echo "🎉 Q&A generation completed successfully!"
echo "📁 Check output files in: $OUTPUT_DIR"
echo "✅ Job completed"

