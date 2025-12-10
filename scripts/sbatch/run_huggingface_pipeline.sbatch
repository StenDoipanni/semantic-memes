#!/bin/bash
#SBATCH --job-name=huggingface_meme_pipeline
#SBATCH --output=logs/slurm/huggingface_meme_pipeline_%j.out
#SBATCH --error=logs/slurm/huggingface_meme_pipeline_%j.err
#SBATCH --partition=gpu_a100
#SBATCH --gpus=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH --time=02:00:00

set -e

echo "🚀 Starting HuggingFace/Transformers Meme Pipeline"
echo "=================================================="
echo "Job ID: $SLURM_JOB_ID"
echo "Node: $SLURM_NODELIST"
echo "GPU: $CUDA_VISIBLE_DEVICES"
echo ""

# Load necessary modules
module load 2023
module load Python/3.11.3-GCCcore-12.3.0
module load CUDA/12.1.1

# Set GPU environment variables
export CUDA_VISIBLE_DEVICES=0
export HUGGINGFACE_DEVICE="cuda"

# Verify CUDA is available
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

# Set pipeline environment variables (before conda activation for model check)
export HUGGINGFACE_MODEL="Qwen/Qwen3-VL-8B-Instruct"

# Activate conda environment
source /home/sdegiorgis/miniconda3/etc/profile.d/conda.sh
conda activate meme-qa-pipeline-env

# Check if Qwen3-VL is being used and ensure transformers is up to date
if [[ "$HUGGINGFACE_MODEL" == *"Qwen3-VL"* ]]; then
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

# Set remaining pipeline environment variables
# API key should be set via environment variable or .env file
# Do not hardcode API keys in version control
# export CLAUDE_API_KEY="${CLAUDE_API_KEY:-}"
export ONTOLOGY_PATH="/home/sdegiorgis/memes/meme-pipeline-server/memes-features/meme-dimensions.ttl"
export PROMPTS_DIR="/home/sdegiorgis/memes/meme-pipeline-server/prompts/dimension-extraction-prompts-refined"
export HUGGINGFACE_DEVICE="cuda"

# Navigate to pipeline directory
cd /home/sdegiorgis/memes/meme-pipeline-server

# Test HuggingFace provider
echo "🧪 Testing HuggingFace provider..."
python3 -c "
import sys
sys.path.insert(0, '/home/sdegiorgis/memes/meme-pipeline-server')
from llm_integration import HuggingFaceProvider
import logging
logging.basicConfig(level=logging.INFO)

print('Initializing HuggingFace provider...')
provider = HuggingFaceProvider()
print(f'✅ Provider initialized: {provider.model_name}')
print(f'✅ Device: {provider.device}')
print(f'✅ Available: {provider.is_available()}')
"

echo "✅ HuggingFace provider ready"
echo ""

# Parse command line arguments for the pipeline
IMAGE_PATH="${1:-sea_monkeys.png}"
MODE="${2:-Core}"

# Resolve bare filenames to ./img directory (keep explicit paths working)
if [[ ! -f "$IMAGE_PATH" ]]; then
    BASENAME_ONLY=$(basename -- "$IMAGE_PATH")
    CANDIDATE_PATH="./img/$BASENAME_ONLY"
    if [[ -f "$CANDIDATE_PATH" ]]; then
        IMAGE_PATH="$CANDIDATE_PATH"
    else
        echo "❌ Error: Image file not found: $IMAGE_PATH"
        echo "Tried also: $CANDIDATE_PATH"
        exit 1
    fi
fi

echo "📊 Configuration:"
echo "  Image: $IMAGE_PATH"
echo "  Mode: $MODE"
echo "  LLM Provider: huggingface"
echo "  Model: $HUGGINGFACE_MODEL"
echo "  Device: $HUGGINGFACE_DEVICE"
echo "  GPU: $CUDA_VISIBLE_DEVICES"
echo ""

# Run the pipeline
echo "🚀 Running meme pipeline with HuggingFace/Transformers..."
echo "=========================================================="
python scripts/py/run_pipeline.py "$IMAGE_PATH" \
    --mode dimension_extraction \
    --dimensions $([ "$MODE" = "All" ] && echo "TextualMaterial VisualMaterial EmotionExpression ColorComposition SceneUnderstanding BackgroundKnowledge Metadata MetaphoricalAndAnalogicalMapping OverallIntent SemioticInterpretation TargetCommunity TemplateStructure ToxicityAssessment" || echo "TextualMaterial VisualMaterial SceneUnderstanding BackgroundKnowledge") \
    --llm-provider huggingface \
    --output-dir ./output

echo ""
echo "🎉 HuggingFace pipeline completed successfully!"
echo "📁 Check output files in: ./output"
echo "✅ Pipeline job completed"

