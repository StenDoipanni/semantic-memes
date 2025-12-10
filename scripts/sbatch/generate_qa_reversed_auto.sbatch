#!/bin/bash
#SBATCH --job-name=generate_qa_reversed_auto
#SBATCH --output=logs/slurm/generate_qa_reversed_auto_%j.out
#SBATCH --error=logs/slurm/generate_qa_reversed_auto_%j.err
#SBATCH --partition=gpu_a100
#SBATCH --gpus=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=02:00:00

set -e  # Exit on any error

# Unbuffer Python output for real-time monitoring
export PYTHONUNBUFFERED=1

echo "🚀 Q&A Generation Pipeline (Reversed - Auto-detect dimensions)"
echo "============================================================="
echo "Job ID: $SLURM_JOB_ID"
echo "Node: $SLURM_NODELIST"
echo "📄 Output file: logs/slurm/generate_qa_reversed_auto_${SLURM_JOB_ID}.out"
echo "📄 Error file: logs/slurm/generate_qa_reversed_auto_${SLURM_JOB_ID}.err"
echo ""

# Determine repo root from script location
# Use BASH_SOURCE[0] which is more reliable than $0 in SLURM
SCRIPT_FILE="${BASH_SOURCE[0]}"
if [[ ! -f "$SCRIPT_FILE" ]]; then
    # Fallback to $0 if BASH_SOURCE not available
    SCRIPT_FILE="$0"
fi

# Get absolute path to script
SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_FILE")" && pwd)"
# Script is in scripts/sbatch, repo root is two levels up
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# If that didn't work, try using SLURM_SUBMIT_DIR and look for the repo
if [[ ! -d "$REPO_ROOT/memes-features" ]] && [[ ! -d "$REPO_ROOT/scripts" ]]; then
    if [[ -n "$SLURM_SUBMIT_DIR" ]]; then
        # Try to find repo root from submit directory
        CANDIDATE="$SLURM_SUBMIT_DIR"
        if [[ -d "$CANDIDATE/memes-features" ]] || [[ -d "$CANDIDATE/scripts" ]]; then
            REPO_ROOT="$CANDIDATE"
        else
            # Try parent directories
            for i in {1..3}; do
                CANDIDATE="$(cd "$CANDIDATE/.." && pwd 2>/dev/null || echo '')"
                if [[ -n "$CANDIDATE" ]] && [[ -d "$CANDIDATE/memes-features" ]] || [[ -d "$CANDIDATE/scripts" ]]; then
                    REPO_ROOT="$CANDIDATE"
                    break
                fi
            done
        fi
    fi
fi

# Final fallback: use hardcoded path if environment variable is set
if [[ -n "$MEME_PIPELINE_ROOT" ]]; then
    REPO_ROOT="$MEME_PIPELINE_ROOT"
fi

# Ensure we have an absolute path and change to it
REPO_ROOT="$(cd "$REPO_ROOT" && pwd)"
cd "$REPO_ROOT"

echo "🔍 DEBUG: Script file: $SCRIPT_FILE"
echo "🔍 DEBUG: Script directory: $SCRIPT_DIR"
echo "🔍 DEBUG: SLURM_SUBMIT_DIR: ${SLURM_SUBMIT_DIR:-not set}"
echo "🔍 DEBUG: Repo root: $REPO_ROOT"
echo "🔍 DEBUG: Current directory: $(pwd)"
echo "🔍 DEBUG: Verifying repo root..."
if [[ -d "$REPO_ROOT/memes-features" ]] || [[ -d "$REPO_ROOT/scripts" ]]; then
    echo "  ✅ Repo root verified (found memes-features or scripts directory)"
else
    echo "  ⚠️  Warning: Repo root might be incorrect"
    echo "  Looking for key directories..."
    ls -la "$REPO_ROOT" 2>/dev/null | head -5 || echo "  (cannot list directory)"
fi
echo ""

# Load necessary modules
echo "🔍 Loading modules..."
module load 2023
module load Python/3.11.3-GCCcore-12.3.0
module load CUDA/12.1.1
echo "✅ Modules loaded"
echo ""

# Set GPU environment variables
export CUDA_VISIBLE_DEVICES=0
export HUGGINGFACE_DEVICE="cuda"
# HUGGINGFACE_MODEL will be set from --llm-model parameter if provided, otherwise use default
export HUGGINGFACE_MODEL="${HUGGINGFACE_MODEL:-Qwen/Qwen3-VL-8B-Instruct}"

# Set pipeline environment variables (using relative paths from repo root)
# API key should be set via environment variable or .env file
# Do not hardcode API keys in version control
# export CLAUDE_API_KEY="${CLAUDE_API_KEY:-}"
export ONTOLOGY_PATH="$REPO_ROOT/memes-features/meme-dimensions.ttl"
export PROMPTS_DIR="$REPO_ROOT/prompts/dimension-extraction-prompts-refined"

echo "🔧 Environment variables set"
echo ""

# Activate conda environment
echo "🔧 Activating conda environment..."
# Try different conda paths (portable across users)
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
    exit 1
fi

echo "✅ Environment activated: $CONDA_DEFAULT_ENV"
echo ""

# Parse command line arguments
# Usage: sbatch generate_qa_reversed_auto.sbatch <image_name> [--image-path PATH] [--llm-provider claude|huggingface] [--llm-model MODEL_NAME] [--output-dir PATH]

IMAGE_NAME=""
IMAGE_PATH=""
OUTPUT_REVERSED_DIR="./output_reversed"
OUTPUT_DIR=""  # Will be set based on image name
LLM_PROVIDER="huggingface"  # Default to HuggingFace
LLM_MODEL=""  # Will be set if --llm-model is provided

while [[ $# -gt 0 ]]; do
    case $1 in
        --image-path)
            IMAGE_PATH="$2"
            shift 2
            ;;
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
        --output-reversed-dir)
            OUTPUT_REVERSED_DIR="$2"
            shift 2
            ;;
        --help)
            echo "Usage: sbatch generate_qa_reversed_auto.sbatch [options]"
            echo ""
            echo "Options:"
            echo "  <image_name>              Image name without extension (optional if --image-path provided)"
            echo "                            Example: sea_monkeys"
            echo "  --image-path PATH          Full path to image file (recommended for vision models)"
            echo "                            If provided, image name is extracted from filename"
            echo "  --llm-provider PROVIDER    LLM provider: claude or huggingface (default: huggingface)"
            echo "  --llm-model MODEL_NAME     HuggingFace model name (e.g., Qwen/Qwen3-VL-30B-A3B-Instruct)"
            echo "                            Default: Qwen/Qwen3-VL-8B-Instruct"
            echo "  --output-dir PATH          Output directory (default: {image_name}_qa_out)"
            echo "  --output-reversed-dir PATH Directory containing reversed pipeline output (default: ./output_reversed)"
            echo ""
            echo "Examples:"
            echo "  sbatch ... sea_monkeys                                    # Uses sea_monkeys as image name"
            echo "  sbatch ... --image-path img/sea_monkeys.png              # Extracts 'sea_monkeys' from path"
            echo "  sbatch ... sea_monkeys --image-path img/sea_monkeys.png # Positional arg is redundant but OK"
            echo "  sbatch ... --llm-provider huggingface --llm-model Qwen/Qwen3-VL-30B-A3B-Instruct"
            echo ""
            echo "Note: The output directory defaults to '{image_name}_qa_out' (e.g., sea_monkeys_qa_out)"
            echo "      The image path is passed to the Q&A generation for vision models like Qwen3-VL"
            exit 0
            ;;
        -*)
            echo "⚠️  Warning: Unknown option: $1 (ignored)"
            shift
            ;;
        *)
            # Positional argument: treat as image name only if we don't have one yet
            if [[ -z "$IMAGE_NAME" && -z "$IMAGE_PATH" ]]; then
                IMAGE_NAME="$1"
            else
                echo "⚠️  Warning: Ignoring extra positional argument: $1"
                echo "   (Image name will be extracted from --image-path if provided)"
            fi
            shift
            ;;
    esac
done

# If image path is provided, extract image name from it (this takes precedence)
if [[ -n "$IMAGE_PATH" ]]; then
    EXTRACTED_NAME=$(basename "$IMAGE_PATH")
    EXTRACTED_NAME="${EXTRACTED_NAME%.*}"
    if [[ -n "$IMAGE_NAME" && "$IMAGE_NAME" != "$EXTRACTED_NAME" ]]; then
        echo "⚠️  Warning: Image name from positional argument ('$IMAGE_NAME') differs from image path ('$EXTRACTED_NAME')"
        echo "   Using name from image path: $EXTRACTED_NAME"
    fi
    IMAGE_NAME="$EXTRACTED_NAME"
    # Convert to absolute path if relative
    if [[ ! "$IMAGE_PATH" =~ ^/ ]]; then
        IMAGE_PATH="$REPO_ROOT/$IMAGE_PATH"
    fi
    # Verify image exists
    if [[ ! -f "$IMAGE_PATH" ]]; then
        echo "⚠️  Warning: Image file not found: $IMAGE_PATH"
        echo "   Will try to find it automatically from TTL filename"
        IMAGE_PATH=""  # Clear it so Python script can try to find it
    fi
fi

# Validate that we have an image name (either from positional arg or extracted from path)
if [[ -z "$IMAGE_NAME" ]]; then
    echo "❌ Error: Could not determine image name"
    echo "   Please provide either:"
    echo "   1. A positional argument: sbatch ... sea_monkeys"
    echo "   2. Or --image-path with a filename that contains the image name"
    exit 1
fi

# Set output directory based on image name (format: output_reversed/{image_name}_qa_out)
if [[ -z "$OUTPUT_DIR" ]]; then
    OUTPUT_DIR="output_reversed/${IMAGE_NAME}_qa_out"
fi

# Validate LLM provider
if [[ "$LLM_PROVIDER" != "claude" && "$LLM_PROVIDER" != "huggingface" ]]; then
    echo "❌ Error: LLM provider must be 'claude' or 'huggingface'"
    exit 1
fi

# Find the TTL file for this image (use absolute path)
# Convert OUTPUT_REVERSED_DIR to absolute path if relative
if [[ ! "$OUTPUT_REVERSED_DIR" =~ ^/ ]]; then
    OUTPUT_REVERSED_DIR="$REPO_ROOT/$OUTPUT_REVERSED_DIR"
fi
TTL_FILE="$OUTPUT_REVERSED_DIR/${IMAGE_NAME}_enhanced_ontology_reversed.ttl"

echo "🔍 DEBUG: Looking for TTL file..."
echo "🔍 DEBUG:   OUTPUT_REVERSED_DIR: $OUTPUT_REVERSED_DIR"
echo "🔍 DEBUG:   TTL_FILE: $TTL_FILE"
echo "🔍 DEBUG:   TTL file exists: $([ -f "$TTL_FILE" ] && echo 'YES' || echo 'NO')"

# If file not found, try alternative locations
if [[ ! -f "$TTL_FILE" ]]; then
    echo "🔍 DEBUG: Primary TTL file not found, trying alternatives..."
    
    # Try with different base paths
    ALTERNATIVE_PATHS=(
        "$REPO_ROOT/output_reversed/${IMAGE_NAME}_enhanced_ontology_reversed.ttl"
        "./output_reversed/${IMAGE_NAME}_enhanced_ontology_reversed.ttl"
        "output_reversed/${IMAGE_NAME}_enhanced_ontology_reversed.ttl"
    )
    
    for alt_path in "${ALTERNATIVE_PATHS[@]}"; do
        if [[ -f "$alt_path" ]]; then
            TTL_FILE="$(cd "$(dirname "$alt_path")" && pwd)/$(basename "$alt_path")"
            OUTPUT_REVERSED_DIR="$(dirname "$TTL_FILE")"
            echo "🔍 DEBUG: Found TTL file at alternative location: $TTL_FILE"
            break
        fi
    done
fi

if [[ -f "$TTL_FILE" ]]; then
    echo "🔍 DEBUG:   TTL file size: $(du -h "$TTL_FILE" | cut -f1)"
    echo "✅ TTL file found: $TTL_FILE"
else
    echo "❌ Error: TTL file not found: $TTL_FILE"
    echo "   Please check:"
    echo "   1. The image name is correct: $IMAGE_NAME"
    echo "   2. Reversed dimension extraction has been run for this image"
    echo "   3. The TTL file exists"
    echo ""
    echo "🔍 DEBUG: Searched in:"
    echo "   - $OUTPUT_REVERSED_DIR"
    echo "   - $REPO_ROOT/output_reversed"
    echo "   - ./output_reversed"
    echo ""
    echo "🔍 DEBUG: Available TTL files:"
    for search_dir in "$OUTPUT_REVERSED_DIR" "$REPO_ROOT/output_reversed" "./output_reversed"; do
        if [[ -d "$search_dir" ]]; then
            echo "   In $search_dir:"
            ls -la "$search_dir"/*.ttl 2>/dev/null | head -3 || echo "     (none found)"
        fi
    done
    exit 1
fi
echo ""

echo "📊 Configuration:"
echo "  Image Name: $IMAGE_NAME"
if [[ -n "$IMAGE_PATH" ]] && [[ -f "$IMAGE_PATH" ]]; then
    echo "  Image Path: $IMAGE_PATH"
    echo "  ✅ Image file exists and will be passed to Q&A generation"
elif [[ -n "$IMAGE_PATH" ]]; then
    echo "  Image Path: $IMAGE_PATH (not found, will try to auto-detect)"
else
    echo "  Image Path: (will try to auto-detect from TTL filename)"
fi
echo "  Output Reversed Directory: $OUTPUT_REVERSED_DIR"
echo "  Output Directory: $OUTPUT_DIR"
echo "  LLM Provider: $LLM_PROVIDER"
if [[ "$LLM_PROVIDER" == "huggingface" ]]; then
    echo "  Model: $HUGGINGFACE_MODEL"
    if [[ -n "$LLM_MODEL" ]]; then
        echo "  Model (from --llm-model): $LLM_MODEL"
    fi
    echo "  Device: $HUGGINGFACE_DEVICE"
fi
echo "  TTL File: $TTL_FILE"
echo ""

# Verify GPU is available (if using huggingface)
if [[ "$LLM_PROVIDER" == "huggingface" ]]; then
    echo "🔍 Verifying GPU access..."
    python3 -c "
import torch
if torch.cuda.is_available():
    print(f'✅ GPU available: {torch.cuda.get_device_name(0)}')
else:
    print('❌ CUDA not available!')
    exit(1)
    " || {
        echo "❌ GPU verification failed!"
        exit 1
    }
    echo ""
fi

# Check if Qwen3-VL is being used and ensure transformers is up to date
if [[ "$LLM_PROVIDER" == "huggingface" && "$HUGGINGFACE_MODEL" == *"Qwen3-VL"* ]]; then
    echo "📦 Installing transformers from source for Qwen3-VL support..."
    echo "⚠️  This may take a few minutes..."
    pip install -q --upgrade git+https://github.com/huggingface/transformers.git || {
        echo "❌ Error: Failed to install transformers from source"
        exit 1
    }
    echo "✅ Transformers updated successfully"
    echo ""
fi

# Create output directory (use absolute path if relative)
if [[ ! "$OUTPUT_DIR" =~ ^/ ]]; then
    OUTPUT_DIR="$REPO_ROOT/$OUTPUT_DIR"
fi
mkdir -p "$OUTPUT_DIR"
echo "📁 Output directory created: $OUTPUT_DIR"
echo ""

# Run Q&A generation using Python script
echo "🚀 Running Q&A generation (auto-detecting dimensions from TTL)..."
echo "================================================================"
echo ""

# Build Python command arguments
PYTHON_ARGS=(
    "$REPO_ROOT/scripts/py/run_qa_from_ttl.py"
    "$TTL_FILE"
    --output-dir "$OUTPUT_DIR"
)

if [[ -n "$LLM_PROVIDER" ]]; then
    PYTHON_ARGS+=(--llm-provider "$LLM_PROVIDER")
fi

# Add image path if provided
if [[ -n "$IMAGE_PATH" ]] && [[ -f "$IMAGE_PATH" ]]; then
    PYTHON_ARGS+=(--image-path "$IMAGE_PATH")
    echo "🖼️  Using image: $IMAGE_PATH"
fi

echo "🐍 Running: python3 ${PYTHON_ARGS[*]}"
echo ""

python3 "${PYTHON_ARGS[@]}"

EXIT_CODE=$?

if [[ $EXIT_CODE -eq 0 ]]; then
    echo ""
    echo "🎉 Q&A generation pipeline completed successfully!"
    echo "📁 Check output files in: $OUTPUT_DIR"
    echo ""
    echo "📋 Generated files:"
    find "$OUTPUT_DIR" -name "*.jsonld" -o -name "*.txt" 2>/dev/null | head -10 || echo "  (check output directory for files)"
else
    echo ""
    echo "❌ Q&A generation pipeline failed with exit code $EXIT_CODE"
    exit $EXIT_CODE
fi

echo "✅ Job completed"
