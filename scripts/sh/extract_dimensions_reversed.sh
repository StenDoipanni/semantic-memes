#!/bin/bash
# Bash script version of extract_dimensions_reversed.sbatch (runs without SLURM)

set -e

echo "🚀 Reversed Dimension Extraction Pipeline"
echo "=========================================="
echo ""

# Get the repository root directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT"

# Fix PyTorch import issue with Intel MKL (missing JIT symbols)
if [[ -f "$REPO_ROOT/libijitstub.so" ]]; then
    export LD_PRELOAD="$REPO_ROOT/libijitstub.so:$LD_PRELOAD"
fi

# Set GPU environment variables (if GPU is available)
export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"
export HUGGINGFACE_DEVICE="${HUGGINGFACE_DEVICE:-cuda}"

# Set pipeline environment variables
# Claude API key should be set via environment variable or .env file
if [[ -z "$CLAUDE_API_KEY" ]]; then
    echo "⚠️  Warning: CLAUDE_API_KEY not set. Please set it in your environment or .env file."
fi

# Set HuggingFace token for authenticated requests (faster downloads, higher rate limits)
export HUGGINGFACE_TOKEN="${HUGGINGFACE_TOKEN:-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}"
export HF_TOKEN="$HUGGINGFACE_TOKEN"
if [[ -n "$HUGGINGFACE_TOKEN" ]]; then
    echo "✅ HuggingFace token set for authenticated requests"
fi

# Set paths relative to repo root
export ONTOLOGY_PATH="${ONTOLOGY_PATH:-$REPO_ROOT/memes-features/meme-dimensions.ttl}"
export PROMPTS_DIR="${PROMPTS_DIR:-$REPO_ROOT/prompts/dimension-extraction-prompts-refined}"

# HUGGINGFACE_MODEL will be set from --llm-model parameter if provided, otherwise use default
export HUGGINGFACE_MODEL="${HUGGINGFACE_MODEL:-Qwen/Qwen3-VL-8B-Instruct}"

# Parse command line arguments
IMAGE_PATH="${1}"
if [[ -z "$IMAGE_PATH" ]]; then
    echo "❌ Error: Image path is required"
    echo ""
    echo "Usage: $0 <image_path> [--llm-provider claude|huggingface] [--llm-model MODEL_NAME] [--output-dir ./output_reversed] [--additional-kb <path> ...] [--iterative-kb true|false] [--refine true|false]"
    echo ""
    echo "Examples:"
    echo "  $0 image.png"
    echo "  $0 image.png --llm-provider claude"
    echo "  $0 image.png --llm-provider huggingface --output-dir ./my_output"
    echo "  $0 image.png --llm-provider huggingface --llm-model Qwen/Qwen3-VL-30B-A3B-Instruct"
    echo "  $0 image.png --additional-kb prompts/dimension-extraction-prompts-refined/AdditionalKnowledgeBase.jsonld"
    echo "  $0 image.png --additional-kb prompts/dimension-extraction-prompts-refined/AdditionalKnowledgeBase.jsonld --iterative-kb true"
    echo "  $0 image.png --additional-kb prompts/dimension-extraction-prompts-refined/AdditionalKnowledgeBase.jsonld --additional-kb prompts/dimension-extraction-prompts-refined/Qua-EntitiesKnowledgeBas.jsonld"
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
REFINE="false"
LLM_MODEL=""  # Will be set if --llm-model is provided
shift

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
        --additional-kb)
            ADDITIONAL_KB+=("$2")
            shift 2
            ;;
        --iterative-kb)
            ITERATIVE_KB="$2"
            shift 2
            ;;
        --refine)
            REFINE="$2"
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
        # Try absolute path first
        if [[ -f "$kb_file" ]]; then
            VALIDATED_KB+=("$kb_file")
        # Try relative to repo root
        elif [[ -f "$REPO_ROOT/$kb_file" ]]; then
            VALIDATED_KB+=("$REPO_ROOT/$kb_file")
        else
            echo "❌ Error: Additional KB file not found: $kb_file"
            echo "   Tried also: $REPO_ROOT/$kb_file"
            exit 1
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

# Resolve image path - try multiple locations
ORIGINAL_IMAGE_PATH="$IMAGE_PATH"
RESOLVED=false

# Try 1: Check if path exists as-is (absolute or relative to current dir)
if [[ -f "$IMAGE_PATH" ]]; then
    RESOLVED=true
    echo "📁 Image found at: $IMAGE_PATH"
# Try 2: Check relative to repo root
elif [[ -f "$REPO_ROOT/$IMAGE_PATH" ]]; then
    IMAGE_PATH="$REPO_ROOT/$IMAGE_PATH"
    RESOLVED=true
    echo "📁 Image found at: $IMAGE_PATH"
# Try 3: Check in img/ directory with full path
elif [[ -f "$REPO_ROOT/img/$IMAGE_PATH" ]]; then
    IMAGE_PATH="$REPO_ROOT/img/$IMAGE_PATH"
    RESOLVED=true
    echo "📁 Image found at: $IMAGE_PATH"
# Try 4: Extract basename and check in img/ directory
else
    BASENAME_ONLY=$(basename -- "$IMAGE_PATH")
    if [[ -f "$REPO_ROOT/img/$BASENAME_ONLY" ]]; then
        IMAGE_PATH="$REPO_ROOT/img/$BASENAME_ONLY"
        RESOLVED=true
        echo "📁 Image found at: $IMAGE_PATH"
    fi
fi

# If still not found, show error with available images
if [[ "$RESOLVED" == "false" ]]; then
    echo "❌ Error: Image file not found: $ORIGINAL_IMAGE_PATH"
    echo ""
    echo "💡 Available images in img/ directory:"
    ls -1 "$REPO_ROOT/img/" 2>/dev/null | sed 's/^/   - /' || echo "   (img/ directory not found)"
    echo ""
    echo "💡 Tip: You can use:"
    echo "   - Full path: /path/to/image.png"
    echo "   - Relative path: ./img/image.png or img/image.png"
    echo "   - Filename only: image.png (will look in ./img/)"
    exit 1
fi

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
    print('⚠️  CUDA not available, will use CPU')
    " || {
        echo "⚠️  Warning: Could not verify GPU. This might be due to PyTorch import issues."
        echo "   Make sure libijitstub.so is available for PyTorch to work."
    }
    echo "✅ GPU check completed"
    echo ""
fi

# Verify Claude API key is set (if using claude)
if [[ "$LLM_PROVIDER" == "claude" ]]; then
    if [[ -z "$CLAUDE_API_KEY" ]]; then
        echo "❌ Error: CLAUDE_API_KEY environment variable is not set!"
        echo "   Please set it before running: export CLAUDE_API_KEY='your-key-here'"
        exit 1
    fi
    # Check if API key looks valid (starts with sk-ant-)
    if [[ ! "$CLAUDE_API_KEY" =~ ^sk-ant- ]]; then
        echo "⚠️  Warning: CLAUDE_API_KEY does not start with 'sk-ant-'"
        echo "   This might indicate an invalid API key format."
    fi
    echo "✅ Claude API key is set (length: ${#CLAUDE_API_KEY} characters)"
    echo ""
fi

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

conda activate meme-qa-pipeline-env

# Check if we're in the right environment
if [[ "$CONDA_DEFAULT_ENV" != "meme-qa-pipeline-env" ]]; then
    echo "❌ Failed to activate meme-qa-pipeline-env environment"
    echo "   Current environment: $CONDA_DEFAULT_ENV"
    exit 1
fi

echo "✅ Environment activated: $CONDA_DEFAULT_ENV"
echo ""

# Verify API key is still available after conda activation (if using claude)
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
    " || {
        echo "❌ Claude API key verification failed!"
        exit 1
    }
    echo ""
fi

# Check if Qwen3-VL is being used and ensure transformers is up to date (if using huggingface)
if [[ "$LLM_PROVIDER" == "huggingface" && "$HUGGINGFACE_MODEL" == *"Qwen3-VL"* ]]; then
    echo "📦 Checking transformers version for Qwen3-VL support..."
    python3 -c "from transformers import Qwen3VLForConditionalGeneration" 2>/dev/null || {
        echo "⚠️  Qwen3-VL support may not be available. Current transformers version:"
        python3 -c "import transformers; print(transformers.__version__)" 2>/dev/null || echo "Could not determine version"
        echo "   You may need to upgrade transformers from source if Qwen3-VL is required."
    }
    echo ""
fi

echo "📊 Configuration:"
echo "  Image: $IMAGE_PATH"
echo "  Pipeline: Reversed (starts with OverallIntent)"
echo "  Dimensions: OverallIntent → TextualMaterial → VisualMaterial → Scene → BackgroundKnowledge → EmotionExpression → AnalogicalMapping → SemioticProjection → ToxicityAssessment → TargetCommunity"
echo "  LLM Provider: $LLM_PROVIDER"
if [[ "$LLM_PROVIDER" == "huggingface" ]]; then
    echo "  Model: $HUGGINGFACE_MODEL"
    if [[ -n "$LLM_MODEL" ]]; then
        echo "  Model (from --llm-model): $LLM_MODEL"
    fi
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

if [[ "$REFINE" == "true" ]]; then
    EXTRACTION_CMD="$EXTRACTION_CMD --refine true"
fi

eval $EXTRACTION_CMD

echo ""
echo "🎉 Reversed dimension extraction completed successfully!"
echo "📁 Check output files in: $OUTPUT_DIR"
echo "✅ Job completed"

