#!/bin/bash
#SBATCH --job-name=extract_dimensions_reversed
#SBATCH --output=logs/slurm/extract_dimensions_reversed_%j.out
#SBATCH --error=logs/slurm/extract_dimensions_reversed_%j.err
#SBATCH --partition=gpu_a100
#SBATCH --gpus=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH --time=02:00:00

set -e

echo "🚀 Reversed Dimension Extraction Pipeline"
echo "=========================================="
echo "Job ID: $SLURM_JOB_ID"
echo "Node: $SLURM_NODELIST"
echo "GPU: $CUDA_VISIBLE_DEVICES"
echo "📄 Output file: logs/slurm/extract_dimensions_reversed_${SLURM_JOB_ID}.out"
echo "📄 Error file: logs/slurm/extract_dimensions_reversed_${SLURM_JOB_ID}.err"
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
export CLAUDE_API_KEY="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"
export ONTOLOGY_PATH="/home/sdegiorgis/memes/meme-pipeline-server/memes-features/meme-dimensions.ttl"
export PROMPTS_DIR="/home/sdegiorgis/memes/meme-pipeline-server/prompts/dimension-extraction-prompts-refined"
export HUGGINGFACE_MODEL="${HUGGINGFACE_MODEL:-Qwen/Qwen3-VL-8B-Instruct}"
export HUGGINGFACE_DEVICE="${HUGGINGFACE_DEVICE:-cuda}"

# Verify Claude API key is set (if using claude)
if [[ "$LLM_PROVIDER" == "claude" ]]; then
    if [[ -z "$CLAUDE_API_KEY" ]]; then
        echo "❌ Error: CLAUDE_API_KEY environment variable is not set!"
        echo "   Please set it in the sbatch file or export it before running."
        exit 1
    fi
    # Check if API key looks valid (starts with sk-ant-)
    if [[ ! "$CLAUDE_API_KEY" =~ ^sk-ant- ]]; then
        echo "⚠️  Warning: CLAUDE_API_KEY does not start with 'sk-ant-'"
        echo "   This might indicate an invalid API key format."
    fi
    echo "✅ Claude API key is set (length: ${#CLAUDE_API_KEY} characters)"
    echo "   Key preview: ${CLAUDE_API_KEY:0:20}...${CLAUDE_API_KEY: -10}"
    echo ""
fi

# Activate conda environment
source /home/sdegiorgis/miniconda3/etc/profile.d/conda.sh
conda activate meme-qa-pipeline-env

# Verify API key is still available after conda activation
if [[ "$LLM_PROVIDER" == "claude" ]]; then
    echo "🔍 Verifying Claude API key after conda activation..."
    python3 -c "
import os
api_key = os.getenv('CLAUDE_API_KEY')
if not api_key:
    print('❌ Error: CLAUDE_API_KEY is not available in Python environment!')
    exit(1)
elif not api_key.startswith('sk-ant-'):
    print('⚠️  Warning: CLAUDE_API_KEY format looks invalid')
    exit(1)
else:
    print(f'✅ Claude API key is available in Python (length: {len(api_key)} chars)')
    print(f'   Key preview: {api_key[:20]}...{api_key[-10:]}')
    "
    if [[ $? -ne 0 ]]; then
        echo "❌ Claude API key verification failed!"
        exit 1
    fi
    echo ""
fi

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
# Usage: sbatch extract_dimensions_reversed.sbatch <image_path> [--llm-provider claude|huggingface] [--output-dir ./output_reversed] [--additional-kb <path> ...] [--iterative-kb true|false]
# Example: sbatch extract_dimensions_reversed.sbatch image.png --llm-provider claude
# Example: sbatch extract_dimensions_reversed.sbatch image.png --additional-kb prompts/dimension-extraction-prompts-refined/AdditionalKnowledgeBase.jsonld --iterative-kb true
# Example: sbatch extract_dimensions_reversed.sbatch image.png --additional-kb prompts/dimension-extraction-prompts-refined/AdditionalKnowledgeBase.jsonld --additional-kb prompts/dimension-extraction-prompts-refined/Qua-EntitiesKnowledgeBas.jsonld

IMAGE_PATH="${1}"
if [[ -z "$IMAGE_PATH" ]]; then
    echo "❌ Error: Image path is required"
    echo ""
    echo "Usage: sbatch extract_dimensions_reversed.sbatch <image_path> [--llm-provider claude|huggingface] [--output-dir ./output_reversed] [--additional-kb <path> ...] [--iterative-kb true|false]"
    echo ""
    echo "Examples:"
    echo "  sbatch extract_dimensions_reversed.sbatch image.png"
    echo "  sbatch extract_dimensions_reversed.sbatch image.png --llm-provider claude"
    echo "  sbatch extract_dimensions_reversed.sbatch image.png --llm-provider huggingface --output-dir ./my_output"
    echo "  sbatch extract_dimensions_reversed.sbatch image.png --additional-kb prompts/dimension-extraction-prompts-refined/AdditionalKnowledgeBase.jsonld"
    echo "  sbatch extract_dimensions_reversed.sbatch image.png --additional-kb prompts/dimension-extraction-prompts-refined/AdditionalKnowledgeBase.jsonld --iterative-kb true"
    echo "  sbatch extract_dimensions_reversed.sbatch image.png --additional-kb prompts/dimension-extraction-prompts-refined/AdditionalKnowledgeBase.jsonld --additional-kb prompts/dimension-extraction-prompts-refined/Qua-EntitiesKnowledgeBas.jsonld"
    echo ""
    echo "Reversed Pipeline Order:"
    echo "  1. OverallIntent (first - graph passed to all subsequent steps)"
    echo "  2. TextualMaterial (receives OverallIntent graph as context)"
    echo "  3. VisualMaterial (receives OverallIntent graph as context)"
    echo "  4. Scene (receives OverallIntent graph + VisualMaterial entities)"
    echo "  5. BackgroundKnowledge (receives OverallIntent graph + VisualMaterial, TextualMaterial, Scene entities)"
    echo "  6. EmotionExpression (receives OverallIntent graph + VisualMaterial, TextualMaterial, Scene, BackgroundKnowledge entities)"
    echo "  7. AnalogicalMapping (receives OverallIntent graph + VisualMaterial, TextualMaterial, Scene, BackgroundKnowledge, EmotionExpression entities)"
    echo "  8. SemioticProjection (receives OverallIntent graph + VisualMaterial, TextualMaterial, Scene, BackgroundKnowledge, AnalogicalMapping entities)"
    echo "  9. ToxicityAssessment (receives OverallIntent graph + VisualMaterial, TextualMaterial, Scene, BackgroundKnowledge, EmotionExpression, AnalogicalMapping, SemioticProjection entities)"
    echo " 10. TargetCommunity (receives OverallIntent graph + VisualMaterial, TextualMaterial, Scene, BackgroundKnowledge, AnalogicalMapping, ToxicityAssessment entities)"
    exit 1
fi

# Parse optional arguments
LLM_PROVIDER="${LLM_PROVIDER:-claude}"
OUTPUT_DIR="${OUTPUT_DIR:-./output_reversed}"
ADDITIONAL_KB=()
ITERATIVE_KB="false"
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
        --additional-kb)
            ADDITIONAL_KB+=("$2")
            shift 2
            ;;
        --iterative-kb)
            ITERATIVE_KB="$2"
            shift 2
            ;;
        *)
            echo "⚠️  Warning: Unknown argument: $1 (ignored)"
            shift
            ;;
    esac
done

# Validate additional KB files if provided
if [[ ${#ADDITIONAL_KB[@]} -gt 0 ]]; then
    VALIDATED_KB=()
    for kb_file in "${ADDITIONAL_KB[@]}"; do
        if [[ ! -f "$kb_file" ]]; then
            # Try relative to pipeline directory
            CANDIDATE_PATH="/home/sdegiorgis/memes/meme-pipeline-server/$kb_file"
            if [[ -f "$CANDIDATE_PATH" ]]; then
                VALIDATED_KB+=("$CANDIDATE_PATH")
            else
                echo "❌ Error: Additional KB file not found: $kb_file"
                echo "   Tried also: $CANDIDATE_PATH"
                exit 1
            fi
        else
            VALIDATED_KB+=("$kb_file")
        fi
    done
    ADDITIONAL_KB=("${VALIDATED_KB[@]}")
    echo "📚 Additional Knowledge Base(s):"
    for kb_file in "${ADDITIONAL_KB[@]}"; do
        echo "   - $kb_file"
    done
    echo "   Iterative KB (attach to all prompts): $ITERATIVE_KB"
    echo ""
fi

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
echo "  Pipeline: Reversed (starts with OverallIntent)"
echo "  Dimensions: OverallIntent → TextualMaterial → VisualMaterial → Scene → BackgroundKnowledge → EmotionExpression → AnalogicalMapping → SemioticProjection → ToxicityAssessment → TargetCommunity"
echo "  LLM Provider: $LLM_PROVIDER"
if [[ "$LLM_PROVIDER" == "huggingface" ]]; then
    echo "  Model: $HUGGINGFACE_MODEL"
    echo "  Device: $HUGGINGFACE_DEVICE"
    echo "  GPU: $CUDA_VISIBLE_DEVICES"
fi
echo "  Output Directory: $OUTPUT_DIR"
echo ""

# Run the extraction
echo "🚀 Running reversed dimension extraction..."
echo "=========================================="
EXTRACTION_CMD="python extract_dimensions_reversed.py \"$IMAGE_PATH\" --llm-provider \"$LLM_PROVIDER\" --output-dir \"$OUTPUT_DIR\""

if [[ ${#ADDITIONAL_KB[@]} -gt 0 ]]; then
    for kb_file in "${ADDITIONAL_KB[@]}"; do
        EXTRACTION_CMD="$EXTRACTION_CMD --additional-kb \"$kb_file\""
    done
    if [[ "$ITERATIVE_KB" == "true" ]]; then
        EXTRACTION_CMD="$EXTRACTION_CMD --iterative-kb true"
    fi
fi

eval $EXTRACTION_CMD

echo ""
echo "🎉 Reversed dimension extraction completed successfully!"
echo "📁 Check output files in: $OUTPUT_DIR"
echo "✅ Job completed"

