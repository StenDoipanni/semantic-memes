#!/bin/bash
#SBATCH --job-name=extract_dimensions
#SBATCH --output=logs/slurm/extract_dimensions_%j.out
#SBATCH --error=logs/slurm/extract_dimensions_%j.err
#SBATCH --partition=gpu_a100
#SBATCH --gpus=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH --time=02:00:00

set -e

echo "🚀 Dimension Extraction Pipeline"
echo "================================="
echo "Job ID: $SLURM_JOB_ID"
echo "Node: $SLURM_NODELIST"
echo "GPU: $CUDA_VISIBLE_DEVICES"
echo "📄 Output file: extract_dimensions_${SLURM_JOB_ID}.out (in submission directory)"
echo "📄 Error file: extract_dimensions_${SLURM_JOB_ID}.err (in submission directory)"
echo ""

# Load necessary modules
module load 2023
module load Python/3.11.3-GCCcore-12.3.0
module load CUDA/12.1.1

# Set GPU environment variables
export CUDA_VISIBLE_DEVICES=0
export HUGGINGFACE_DEVICE="cuda"

# Verify CUDA is available (if using huggingface)
if [[ "$LLM_PROVIDER" == "huggingface" ]]; then
    echo "🔍 Verifying GPU access..."
    python3 -c "
import torch
print(f'CUDA available: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'GPU Device: {torch.cuda.get_device_name(0)}')
    print(f'GPU Count: {torch.cuda.device_count()}')
else:
    print('❌ CUDA not available!')
    exit(1)
    "
    echo "✅ GPU verified and ready"
    echo ""
fi

# Set pipeline environment variables
# API key should be set via environment variable or .env file
# Do not hardcode API keys in version control
# export CLAUDE_API_KEY="${CLAUDE_API_KEY:-}"
export ONTOLOGY_PATH="/home/sdegiorgis/memes/meme-pipeline-server/memes-features/meme-dimensions.ttl"
export PROMPTS_DIR="/home/sdegiorgis/memes/meme-pipeline-server/prompts/dimension-extraction-prompts-refined"
export HUGGINGFACE_MODEL="${HUGGINGFACE_MODEL:-Qwen/Qwen3-VL-8B-Instruct}"
export HUGGINGFACE_DEVICE="${HUGGINGFACE_DEVICE:-cuda}"

# Activate conda environment
source /home/sdegiorgis/miniconda3/etc/profile.d/conda.sh
conda activate meme-qa-pipeline-env

# Check if Qwen3-VL is being used and ensure transformers is up to date (if using huggingface)
if [[ "$LLM_PROVIDER" == "huggingface" && "$HUGGINGFACE_MODEL" == *"Qwen3-VL"* ]]; then
    echo "📦 Installing transformers from source for Qwen3-VL support..."
    echo "⚠️  This may take a few minutes..."
    pip install -q --upgrade git+https://github.com/huggingface/transformers.git || {
        echo "❌ Error: Failed to install transformers from source"
        echo "Please install manually with: pip install git+https://github.com/huggingface/transformers.git"
        exit 1
    }
    echo "✅ Transformers updated successfully"
    echo ""
fi

# Navigate to pipeline directory
cd /home/sdegiorgis/memes/meme-pipeline-server

# Parse command line arguments
# Usage: sbatch extract_dimensions.sbatch <image_path> [dimension1] [dimension2] ... [--llm-provider claude|huggingface]
# Example: sbatch extract_dimensions.sbatch image.png VisualMaterial TextualMaterial EmotionExpression --llm-provider claude

IMAGE_PATH="${1}"
if [[ -z "$IMAGE_PATH" ]]; then
    echo "❌ Error: Image path is required"
    echo ""
    echo "Usage: sbatch extract_dimensions.sbatch <image_path> [dimension1] [dimension2] ... [--llm-provider claude|huggingface]"
    echo ""
    echo "Examples:"
    echo "  sbatch extract_dimensions.sbatch image.png VisualMaterial TextualMaterial"
    echo "  sbatch extract_dimensions.sbatch image.png EmotionExpression --llm-provider claude"
    echo "  sbatch extract_dimensions.sbatch image.png VisualMaterial TextualMaterial SceneUnderstanding BackgroundKnowledge --llm-provider huggingface"
    echo ""
    echo "Available dimensions:"
    echo "  VisualMaterial TextualMaterial EmotionExpression ColorComposition"
    echo "  SceneUnderstanding BackgroundKnowledge Metadata"
    echo "  MetaphoricalAndAnalogicalMapping OverallIntent SemioticInterpretation"
    echo "  TargetCommunity TemplateStructure ToxicityAssessment"
    exit 1
fi

# Parse dimensions and LLM provider from arguments
DIMENSIONS=()
LLM_PROVIDER="${LLM_PROVIDER:-claude}"
shift

while [[ $# -gt 0 ]]; do
    case $1 in
        --llm-provider)
            LLM_PROVIDER="$2"
            shift 2
            ;;
        --output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        *)
            # Treat as dimension name
            DIMENSIONS+=("$1")
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

# If no dimensions specified, show error
if [[ ${#DIMENSIONS[@]} -eq 0 ]]; then
    echo "❌ Error: At least one dimension must be specified"
    echo ""
    echo "Available dimensions:"
    echo "  VisualMaterial TextualMaterial EmotionExpression ColorComposition"
    echo "  SceneUnderstanding BackgroundKnowledge Metadata"
    echo "  MetaphoricalAndAnalogicalMapping OverallIntent SemioticInterpretation"
    echo "  TargetCommunity TemplateStructure ToxicityAssessment"
    exit 1
fi

# Set default output directory if not specified
OUTPUT_DIR="${OUTPUT_DIR:-./output}"

echo "📊 Configuration:"
echo "  Image: $IMAGE_PATH"
echo "  Dimensions: ${DIMENSIONS[*]}"
echo "  LLM Provider: $LLM_PROVIDER"
if [[ "$LLM_PROVIDER" == "huggingface" ]]; then
    echo "  Model: $HUGGINGFACE_MODEL"
    echo "  Device: $HUGGINGFACE_DEVICE"
    echo "  GPU: $CUDA_VISIBLE_DEVICES"
fi
echo "  Output Directory: $OUTPUT_DIR"
echo ""

# Run the extraction
echo "🚀 Running dimension extraction..."
echo "=================================="
python extract_dimensions.py "$IMAGE_PATH" \
    --dimensions "${DIMENSIONS[@]}" \
    --llm-provider "$LLM_PROVIDER" \
    --output-dir "$OUTPUT_DIR"

echo ""
echo "🎉 Dimension extraction completed successfully!"
echo "📁 Check output files in: $OUTPUT_DIR"
echo "✅ Job completed"

