#!/bin/bash

# Q&A Generation Pipeline Script for Reversed Pipeline
# This script generates Q&A pairs from extracted meme dimensions
# Supports specifying specific dimensions and individuals

set -e  # Exit on any error

# Default configuration
IMAGE_PATH=""  # Full path to image file (required)
IMAGE_NAME=""  # Will be extracted from image path
OUTPUT_REVERSED_DIR="./output_reversed"
OUTPUT_DIR="./output_reversed/qa"
LLM_PROVIDER="claude"
CONDA_ENV="meme-qa-pipeline-env"
DIMENSIONS=""  # Comma-separated list of dimensions to process (empty = all)
INDIVIDUALS=""  # Comma-separated list of specific individuals (format: DimensionName:instance1,instance2)
USE_TTL=false  # Use TTL file instead of JSON-LD files
TTL_FILE=""  # Path to TTL file (optional, will be auto-detected if not provided)
QUESTIONS_PER_DIMENSION=1  # Number of questions to generate per dimension (default: 1)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Q&A Generation Pipeline (Reversed)${NC}"
echo "=============================================="

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

echo -e "${GREEN}🔧 Environment variables set${NC}"

# Function to show help
show_help() {
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  --image-path PATH          Full path to image file (required)"
    echo "  --output-reversed-dir PATH  Directory containing reversed pipeline output (default: $OUTPUT_REVERSED_DIR)"
    echo "  --output-dir PATH           Output directory for Q&A files (default: $OUTPUT_DIR)"
    echo "  --llm-provider PROVIDER     LLM provider: claude or huggingface (default: $LLM_PROVIDER)"
    echo "  --dimensions LIST           Comma-separated list of dimensions to process (default: all)"
    echo "                             Example: OverallIntent,Scene,EmotionExpression"
    echo "  --individuals SPEC          Comma-separated list of specific individuals"
    echo "                             Format: DimensionName:instance1,instance2"
    echo "                             Example: EmotionExpression:amusement,joy"
    echo "  --use-ttl                   Use TTL file instead of JSON-LD files"
    echo "  --ttl-file PATH             Path to TTL file (optional, auto-detected if not provided)"
    echo "  --questions-per-dimension N Number of questions to generate per dimension (default: 1)"
    echo "  --help                      Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --image-path ./img/sea_monkeys.png"
    echo "  $0 --image-path ./img/01235.png --dimensions OverallIntent,Scene"
    echo "  $0 --image-path ./img/01235.png --individuals EmotionExpression:amusement,joy"
    echo "  $0 --image-path ./img/01235.png --use-ttl"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --image-path)
            IMAGE_PATH="$2"
            shift 2
            ;;
        --output-reversed-dir)
            OUTPUT_REVERSED_DIR="$2"
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
        --dimensions)
            DIMENSIONS="$2"
            shift 2
            ;;
        --individuals)
            INDIVIDUALS="$2"
            shift 2
            ;;
        --use-ttl)
            USE_TTL=true
            shift
            ;;
        --ttl-file)
            TTL_FILE="$2"
            shift 2
            ;;
        --questions-per-dimension)
            QUESTIONS_PER_DIMENSION="$2"
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
    echo -e "${RED}❌ Error: --image-path is required${NC}"
    echo "Use --help for usage information"
    exit 1
fi

# Validate that the provided image path exists
if [[ ! -f "$IMAGE_PATH" ]]; then
    echo -e "${RED}❌ Error: Image file not found: $IMAGE_PATH${NC}"
    exit 1
fi

# Extract image name from path
IMAGE_BASENAME=$(basename -- "$IMAGE_PATH")
IMAGE_NAME="${IMAGE_BASENAME%.*}"

if [[ ! -d "$OUTPUT_REVERSED_DIR" ]]; then
    echo -e "${RED}❌ Error: Output reversed directory not found: $OUTPUT_REVERSED_DIR${NC}"
    exit 1
fi

DIMENSIONS_DIR="$OUTPUT_REVERSED_DIR/dimensions"
if [[ ! -d "$DIMENSIONS_DIR" ]]; then
    echo -e "${RED}❌ Error: Dimensions directory not found: $DIMENSIONS_DIR${NC}"
    exit 1
fi

if [[ "$LLM_PROVIDER" != "claude" && "$LLM_PROVIDER" != "huggingface" ]]; then
    echo -e "${RED}❌ Error: LLM provider must be 'claude' or 'huggingface'${NC}"
    exit 1
fi

# Display configuration
echo -e "${YELLOW}📋 Configuration:${NC}"
echo "  Image Path: $IMAGE_PATH"
echo "  Image Name (extracted): $IMAGE_NAME"
if [[ -f "$IMAGE_PATH" ]]; then
    echo -e "  ${GREEN}✅ Image file exists${NC}"
else
    echo -e "  ${YELLOW}⚠️  Image file not found${NC}"
fi
echo "  Output Reversed Directory: $OUTPUT_REVERSED_DIR"
echo "  Dimensions Directory: $DIMENSIONS_DIR"
echo "  Output Directory: $OUTPUT_DIR"
echo "  LLM Provider: $LLM_PROVIDER"
echo "  Conda Environment: $CONDA_ENV"
if [[ -n "$DIMENSIONS" ]]; then
    echo "  Dimensions to Process: $DIMENSIONS"
fi
if [[ -n "$INDIVIDUALS" ]]; then
    echo "  Specific Individuals: $INDIVIDUALS"
fi
if [[ "$USE_TTL" == true ]]; then
    echo "  Using TTL file: Yes"
    if [[ -n "$TTL_FILE" ]]; then
        echo "  TTL File Path: $TTL_FILE"
    fi
fi
echo "  Questions per dimension: $QUESTIONS_PER_DIMENSION"
echo ""

# Activate conda environment
echo -e "${BLUE}🔧 Activating conda environment...${NC}"
# Try different conda paths
if [ -f ~/miniconda3/etc/profile.d/conda.sh ]; then
    source ~/miniconda3/etc/profile.d/conda.sh
elif [ -f /opt/miniconda3/etc/profile.d/conda.sh ]; then
    source /opt/miniconda3/etc/profile.d/conda.sh
elif [ -f ~/anaconda3/etc/profile.d/conda.sh ]; then
    source ~/anaconda3/etc/profile.d/conda.sh
else
    echo -e "${YELLOW}⚠️  Conda not found in standard locations, trying direct activation...${NC}"
fi

conda activate "$CONDA_ENV"

# Check if we're in the right environment
if [[ "$CONDA_DEFAULT_ENV" != "$CONDA_ENV" ]]; then
    echo -e "${RED}❌ Failed to activate $CONDA_ENV environment${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Environment activated: $CONDA_DEFAULT_ENV${NC}"
echo ""

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

# Create output directory
mkdir -p "$OUTPUT_DIR"
echo -e "${GREEN}📁 Output directory created: $OUTPUT_DIR${NC}"

# Check if dimensions exist
DIMENSION_COUNT=$(find "$DIMENSIONS_DIR" -maxdepth 1 -type d | wc -l)
DIMENSION_COUNT=$((DIMENSION_COUNT - 1))  # Subtract 1 for the directory itself

if [[ $DIMENSION_COUNT -eq 0 ]]; then
    echo -e "${RED}❌ Error: No dimension folders found in $DIMENSIONS_DIR${NC}"
    echo "Please run reversed dimension extraction first"
    exit 1
fi

echo -e "${GREEN}📊 Found $DIMENSION_COUNT dimension folders${NC}"

# List available dimensions
echo -e "${YELLOW}📋 Available dimensions:${NC}"
for dim_dir in "$DIMENSIONS_DIR"/*; do
    if [[ -d "$dim_dir" ]]; then
        dim_name=$(basename "$dim_dir")
        # Count files for this specific image
        file_count=$(find "$dim_dir" -name "${IMAGE_NAME}_*.jsonld" -o -name "${IMAGE_NAME}_*.jsonld" | wc -l)
        if [[ $file_count -eq 0 ]]; then
            # Try without image name prefix
            file_count=$(find "$dim_dir" -name "*.jsonld" | wc -l)
        fi
        echo "  - $dim_name ($file_count files)"
    fi
done
echo ""

# Run Q&A generation
echo -e "${BLUE}🚀 Starting Q&A generation...${NC}"
echo "=================================="

# Export environment variables for Python script
export IMAGE_NAME="$IMAGE_NAME"
export IMAGE_PATH="$IMAGE_PATH"
export DIMENSIONS_DIR="$DIMENSIONS_DIR"
export OUTPUT_DIR="$OUTPUT_DIR"
export OUTPUT_REVERSED_DIR="$OUTPUT_REVERSED_DIR"
export LLM_PROVIDER="$LLM_PROVIDER"
export USE_TTL="$USE_TTL"
export TTL_FILE="${TTL_FILE:-}"
export DIMENSIONS="$DIMENSIONS"
export INDIVIDUALS="$INDIVIDUALS"
export QUESTIONS_PER_DIMENSION="${QUESTIONS_PER_DIMENSION:-1}"

python3 << 'PYTHON_SCRIPT'
import sys
import os
from pathlib import Path

# Enable better error reporting
import traceback
sys.excepthook = lambda exc_type, exc_value, exc_traceback: (
    print(f'❌ Python Error: {exc_type.__name__}: {exc_value}', flush=True),
    traceback.print_exception(exc_type, exc_value, exc_traceback, file=sys.stderr)
)

# Debug: Print Python executable and path
print(f'🐍 Python executable: {sys.executable}', flush=True)
print(f'🐍 Python version: {sys.version}', flush=True)
print(f'🐍 Python path: {sys.path[:3]}', flush=True)

# Add project root to path
project_root = Path(os.environ.get('OUTPUT_REVERSED_DIR', './output_reversed')).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Debug: Verify rdflib is accessible before importing
try:
    import rdflib
    print(f'✅ rdflib is accessible (version: {rdflib.__version__})', flush=True)
except ImportError as e:
    print(f'❌ Error: rdflib is not accessible: {e}', flush=True)
    print(f'   Python executable: {sys.executable}', flush=True)
    print(f'   Python path: {sys.path}', flush=True)
    sys.exit(1)

# Configuration from environment
image_name = os.environ.get('IMAGE_NAME', '')
image_path_str = os.environ.get('IMAGE_PATH', '')
dimensions_dir_str = os.environ.get('DIMENSIONS_DIR', '')
output_dir_str = os.environ.get('OUTPUT_DIR', '')
llm_provider = os.environ.get('LLM_PROVIDER', 'claude')
use_ttl = os.environ.get('USE_TTL', 'false').lower() == 'true'
dimensions_filter_str = os.environ.get('DIMENSIONS', '')
individuals_filter_str = os.environ.get('INDIVIDUALS', '')
questions_per_dimension = int(os.environ.get('QUESTIONS_PER_DIMENSION', '1'))

# Set HuggingFace token if available
hf_token = os.environ.get('HUGGINGFACE_TOKEN') or os.environ.get('HF_TOKEN')
if hf_token:
    os.environ['HF_TOKEN'] = hf_token
    os.environ['HUGGINGFACE_TOKEN'] = hf_token

# Convert to Path objects
image_path = Path(image_path_str) if image_path_str else None
dimensions_dir = Path(dimensions_dir_str) if dimensions_dir_str else None
output_dir = Path(output_dir_str) if output_dir_str else None

# CRITICAL: Extract image name from image path if they don't match
# This ensures we use the correct image name for TTL files and dimension files
if image_path and image_path.exists():
    image_name_from_path = image_path.stem  # Get filename without extension
    if image_name != image_name_from_path:
        print(f'⚠️  Warning: Image name mismatch detected!', flush=True)
        print(f'   IMAGE_NAME from env: {image_name}', flush=True)
        print(f'   Image name from path: {image_name_from_path}', flush=True)
        print(f'   Updating IMAGE_NAME to match image path: {image_name_from_path}', flush=True)
        image_name = image_name_from_path

# Validate and resolve image path
if image_path is None or not image_path.exists():
    # Try to find image based on image_name
    output_reversed_dir = Path(os.environ.get('OUTPUT_REVERSED_DIR', './output_reversed'))
    
    # Try multiple locations
    possible_paths = [
        output_reversed_dir.parent / 'img' / f"{image_name}.png",
        output_reversed_dir.parent / 'img' / f"{image_name}.jpg",
        output_reversed_dir.parent / 'img' / f"{image_name}.jpeg",
        Path('img') / f"{image_name}.png",
        Path('img') / f"{image_name}.jpg",
        Path('img') / f"{image_name}.jpeg",
    ]
    
    for candidate_path in possible_paths:
        if candidate_path.exists():
            image_path = candidate_path
            print(f'🔍 Found image at: {image_path}', flush=True)
            break
    
    if image_path is None or not image_path.exists():
        print(f'❌ Error: Image file not found for {image_name}', flush=True)
        print(f'   Tried paths: {possible_paths}', flush=True)
        sys.exit(1)

print(f'🖼️  Processing image: {image_name}')
print(f'🖼️  Image path: {image_path}')
print(f'🖼️  Image exists: {image_path.exists() if image_path else False}')
print(f'📊 Dimensions directory: {dimensions_dir}')
print(f'💾 Output directory: {output_dir}')
print(f'🤖 LLM Provider: {llm_provider}')
print('')

# Check if TTL file exists and should be used
output_reversed_dir = Path(os.environ.get('OUTPUT_REVERSED_DIR', './output_reversed'))

# Use the corrected image_name (which may have been updated from image path)
refined_ttl_file = output_reversed_dir / f"{image_name}_refined_ontology.ttl"
enhanced_ttl_file = output_reversed_dir / f"{image_name}_enhanced_ontology_reversed.ttl"

print(f'🔍 Looking for TTL files with image name: {image_name}', flush=True)
print(f'   Refined TTL: {refined_ttl_file}', flush=True)
print(f'   Enhanced TTL: {enhanced_ttl_file}', flush=True)

# Auto-detect TTL file if not explicitly set
ttl_file = None
if not use_ttl:
    if refined_ttl_file.exists():
        print(f'📄 Found refined ontology TTL file: {refined_ttl_file}', flush=True)
        use_ttl = True
        ttl_file = refined_ttl_file
    elif enhanced_ttl_file.exists():
        print(f'📄 Found enhanced ontology TTL file: {enhanced_ttl_file}', flush=True)
        use_ttl = True
        ttl_file = enhanced_ttl_file
    else:
        print(f'📄 No TTL file found, will use JSON-LD files from dimensions directory', flush=True)
        print(f'   Looked for: {refined_ttl_file} or {enhanced_ttl_file}', flush=True)

# Determine TTL file path
if use_ttl:
    # Get TTL file path from environment, auto-detection, or construct it
    if ttl_file is None:
        ttl_file_str = os.environ.get('TTL_FILE', '')
        if ttl_file_str:
            ttl_file = Path(ttl_file_str)
        else:
            # Try refined_ontology.ttl first (the correct file name)
            ttl_file = output_reversed_dir / f"{image_name}_refined_ontology.ttl"
            # Fallback to enhanced_ontology_reversed.ttl for backwards compatibility
            if not ttl_file.exists():
                ttl_file = output_reversed_dir / f"{image_name}_enhanced_ontology_reversed.ttl"
    
    if not ttl_file.exists():
        print(f'❌ Error: TTL file not found: {ttl_file}')
        sys.exit(1)
    
    print(f'📄 Using TTL file: {ttl_file}')
    
    # Import Q&A generation module
    from qa_generation_module import QAGenerationModule
    
    qa_module = QAGenerationModule(llm_provider=llm_provider)
    
    # Use standard dimensions list from config (with name corrections for TTL files)
    # This ensures we process ALL dimensions we're interested in, not just those with instances
    all_dimensions = qa_module.get_standard_dimensions()
    
    if not all_dimensions:
        print(f'❌ Error: No standard dimensions found')
        sys.exit(1)
    
    # Parse dimensions filter if provided
    dimensions_to_process = all_dimensions
    if dimensions_filter_str:
        dimensions_filter = [d.strip() for d in dimensions_filter_str.split(',')]
        dimensions_to_process = [d for d in all_dimensions if d in dimensions_filter]
        print(f'📋 Filtering to {len(dimensions_to_process)} dimension(s): {", ".join(dimensions_to_process)}')
    else:
        print(f'📋 Processing all {len(dimensions_to_process)} dimension(s) found in TTL file: {", ".join(dimensions_to_process)}')
    
    total_qa_pairs = 0
    dimensions_processed = []
    dimensions_with_instances = []
    dimensions_without_instances = []
    errors = []
    
    # Process each dimension
    for dimension_name in dimensions_to_process:
        print(f'\\n📊 Processing dimension: {dimension_name}')
        print(f'🖼️  Using image: {image_path.name} (path: {image_path})', flush=True)
        
        # Generate Q&A directly from TTL file
        qa_result = qa_module.generate_qa_for_dimension_from_ttl(
            dimension_name=dimension_name,
            ttl_file=ttl_file,
            image_path=image_path,
            output_dir=output_dir,
            questions_per_dimension=questions_per_dimension
        )
        
        if qa_result["success"]:
            dimensions_processed.append(dimension_name)
            total_qa_pairs += qa_result.get("qa_pairs", 0)
            instances_count = qa_result.get("instances_count", 0)
            
            if instances_count > 0:
                dimensions_with_instances.append(dimension_name)
                print(f'✅ Generated Q&A for {dimension_name} ({instances_count} individual(s) found)')
            else:
                dimensions_without_instances.append(dimension_name)
                print(f'✅ Generated Q&A for {dimension_name} (no individuals, used dimension description)')
        else:
            error_msg = f"Failed to generate Q&A for {dimension_name}: {qa_result.get('error', 'Unknown error')}"
            errors.append(error_msg)
            print(f'❌ {error_msg}')
    
    # Print summary
    print('\\n' + '=' * 50)
    print(f'✅ Q&A generation completed!')
    print(f'📊 Dimensions processed: {len(dimensions_processed)}')
    print(f'❓ Total Q&A pairs generated: {total_qa_pairs}')
    
    if dimensions_with_instances:
        print(f'\\n📋 Dimensions with individuals ({len(dimensions_with_instances)}):')
        for dim in dimensions_with_instances:
            print(f'  - {dim}')
    
    if dimensions_without_instances:
        print(f'\\n📋 Dimensions without individuals ({len(dimensions_without_instances)}):')
        for dim in dimensions_without_instances:
            print(f'  - {dim} (used dimension description only)')
    
    if errors:
        print(f'\\n⚠️  Errors encountered:')
        for error in errors:
            print(f'  - {error}')
    
    if not dimensions_processed:
        print('\\n❌ No Q&A pairs were generated')
        sys.exit(1)
else:
    # Use JSON-LD based Q&A generation with filtering
    try:
        from qa_generation_module import QAGenerationModule
    except Exception as e:
        print(f'❌ Error importing QAGenerationModule: {e}', flush=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    try:
        qa_module = QAGenerationModule(llm_provider=llm_provider)
    except Exception as e:
        print(f'❌ Error initializing QAGenerationModule: {e}', flush=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Parse dimensions filter
    dimensions_filter = None
    if dimensions_filter_str:
        dimensions_filter = [d.strip() for d in dimensions_filter_str.split(',')]
    
    # Parse individuals filter
    individuals_filter = {}
    if individuals_filter_str:
        for spec in individuals_filter_str.split(','):
            if ':' in spec:
                dim_name, instances = spec.split(':', 1)
                dim_name = dim_name.strip()
                instances_list = [i.strip() for i in instances.split(',')]
                individuals_filter[dim_name] = instances_list
    
    # Get dimension folders
    if not dimensions_dir or not dimensions_dir.exists():
        print(f'❌ Error: Dimensions directory not found: {dimensions_dir}')
        sys.exit(1)
    
    dimension_folders = [d for d in dimensions_dir.iterdir() if d.is_dir()]
    
    if dimensions_filter:
        dimension_folders = [d for d in dimension_folders if d.name in dimensions_filter]
        print(f'📋 Filtering to {len(dimension_folders)} dimension(s): {", ".join(dimensions_filter)}')
    
    if not dimension_folders:
        print(f'❌ Error: No dimension folders found matching criteria')
        sys.exit(1)
    
    print(f'📋 Processing {len(dimension_folders)} dimension(s)')
    
    total_qa_pairs = 0
    dimensions_processed = []
    errors = []
    
    for dimension_folder in dimension_folders:
        dimension_name = dimension_folder.name
        
        # Get JSON-LD files for this dimension
        # ONLY use files that match the image name prefix - no fallback!
        dimension_files = list(dimension_folder.glob(f"{image_name}_*.jsonld"))
        
        if not dimension_files:
            print(f'⚠️  Warning: No JSON-LD files found for {dimension_name} with prefix {image_name}_', flush=True)
            print(f'   Looking in: {dimension_folder}', flush=True)
            available_files = list(dimension_folder.glob("*.jsonld"))
            print(f'   Available files: {[f.name for f in available_files]}', flush=True)
            warning = f"No matching JSON-LD files found for {dimension_name} with image prefix {image_name}_"
            errors.append(warning)
            continue
        
        # Debug: Show which files are being used
        print(f'📄 Using dimension files: {[f.name for f in dimension_files]}', flush=True)
        
        # Apply individuals filter if specified
        if dimension_name in individuals_filter:
            filtered_files = []
            for file_path in dimension_files:
                # Extract instance name from filename
                instance_name = file_path.stem.replace(f"{image_name}_", "").replace(f"{dimension_name}_", "")
                # Try to match against filter
                for filter_instance in individuals_filter[dimension_name]:
                    if filter_instance.lower() in instance_name.lower() or instance_name.lower() in filter_instance.lower():
                        filtered_files.append(file_path)
                        break
            dimension_files = filtered_files
            print(f'  Filtered to {len(dimension_files)} individual(s) for {dimension_name}')
        
        if not dimension_files:
            warning = f"No matching JSON-LD files found for {dimension_name} after filtering"
            print(f'⚠️  {warning}')
            errors.append(warning)
            continue
        
        print(f'\\n📊 Processing {dimension_name} ({len(dimension_files)} file(s))')
        print(f'🖼️  Using image: {image_path.name} (path: {image_path})', flush=True)
        
        # Generate Q&A for this dimension
        qa_result = qa_module.generate_qa_for_dimension(
            dimension_name=dimension_name,
            dimension_files=dimension_files,
            image_path=image_path,
            output_dir=output_dir
        )
        
        if qa_result["success"]:
            dimensions_processed.append(dimension_name)
            total_qa_pairs += qa_result.get("qa_pairs", 0)
            print(f'✅ Generated {qa_result.get("qa_pairs", 0)} Q&A pair(s) for {dimension_name}')
        else:
            error_msg = f"Failed to generate Q&A for {dimension_name}: {qa_result.get('error', 'Unknown error')}"
            errors.append(error_msg)
            print(f'❌ {error_msg}')
    
    # Print summary
    print('\\n' + '=' * 50)
    print(f'✅ Q&A generation completed!')
    print(f'📊 Dimensions processed: {len(dimensions_processed)}')
    print(f'❓ Total Q&A pairs generated: {total_qa_pairs}')
    
    if dimensions_processed:
        print(f'\\n📋 Processed dimensions:')
        for dim in dimensions_processed:
            print(f'  - {dim}')
    
    if errors:
        print(f'\\n⚠️  Errors encountered:')
        for error in errors:
            print(f'  - {error}')
    
    if not dimensions_processed:
        print('\\n❌ No Q&A pairs were generated')
        sys.exit(1)
PYTHON_SCRIPT

# Capture exit code
PYTHON_EXIT_CODE=$?

# Check if the Python script succeeded
if [[ $PYTHON_EXIT_CODE -eq 0 ]]; then
    echo ""
    echo -e "${GREEN}🎉 Q&A generation pipeline completed successfully!${NC}"
    echo ""
    echo -e "${YELLOW}📁 Output files saved to: $OUTPUT_DIR${NC}"
    echo ""
    echo -e "${BLUE}📋 Generated files:${NC}"
    find "$OUTPUT_DIR" -name "*.jsonld" -o -name "*.txt" 2>/dev/null | head -10
    if [[ $(find "$OUTPUT_DIR" -name "*.jsonld" -o -name "*.txt" 2>/dev/null | wc -l) -gt 10 ]]; then
        echo "  ... and more files"
    fi
else
    echo ""
    echo -e "${RED}❌ Q&A generation pipeline failed with exit code: $PYTHON_EXIT_CODE${NC}"
    echo -e "${YELLOW}💡 Check the error messages above for details${NC}"
    exit $PYTHON_EXIT_CODE
fi

