#!/bin/bash

# Q&A Generation Pipeline Script for Reversed Pipeline
# This script generates Q&A pairs from extracted meme dimensions
# Supports specifying specific dimensions and individuals

set -e  # Exit on any error

# Default configuration
IMAGE_NAME="sea_monkeys"  # Base name without extension
IMAGE_PATH=""  # Full path to image file (optional, will be auto-detected if not provided)
OUTPUT_REVERSED_DIR="./output_reversed"
OUTPUT_DIR="./output_reversed/qa"
LLM_PROVIDER="claude"
CONDA_ENV="meme-qa-pipeline-env"
DIMENSIONS=""  # Comma-separated list of dimensions to process (empty = all)
INDIVIDUALS=""  # Comma-separated list of specific individuals (format: DimensionName:instance1,instance2)
USE_TTL=false  # Use TTL file instead of JSON-LD files
TTL_FILE=""  # Path to TTL file (optional, will be auto-detected if not provided)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Q&A Generation Pipeline (Reversed)${NC}"
echo "=============================================="

# Set environment variables first
# API key should be set via environment variable or .env file
# Do not hardcode API keys in version control
# export CLAUDE_API_KEY="${CLAUDE_API_KEY:-}"
export ONTOLOGY_PATH="/home/sdegiorgis/memes/meme-pipeline-server/memes-features/meme-dimensions.ttl"
export PROMPTS_DIR="/home/sdegiorgis/memes/meme-pipeline-server/prompts/dimension-extraction-prompts-refined"
export HUGGINGFACE_MODEL="${HUGGINGFACE_MODEL:-Qwen/Qwen3-VL-8B-Instruct}"
export HUGGINGFACE_DEVICE="${HUGGINGFACE_DEVICE:-cuda}"

echo -e "${GREEN}🔧 Environment variables set${NC}"

# Function to show help
show_help() {
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  --image-name NAME          Base image name without extension (default: $IMAGE_NAME)"
    echo "  --image-path PATH          Full path to image file (optional, auto-detected if not provided)"
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
    echo "  --help                      Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --image-name sea_monkeys"
    echo "  $0 --image-name sea_monkeys --dimensions OverallIntent,Scene"
    echo "  $0 --image-name sea_monkeys --individuals EmotionExpression:amusement,joy"
    echo "  $0 --image-name sea_monkeys --use-ttl"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --image-name)
            IMAGE_NAME="$2"
            shift 2
            ;;
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
if [[ ! -d "$OUTPUT_REVERSED_DIR" ]]; then
    echo -e "${RED}❌ Error: Output reversed directory not found: $OUTPUT_REVERSED_DIR${NC}"
    exit 1
fi

DIMENSIONS_DIR="$OUTPUT_REVERSED_DIR/dimensions"
if [[ ! -d "$DIMENSIONS_DIR" ]]; then
    echo -e "${RED}❌ Error: Dimensions directory not found: $DIMENSIONS_DIR${NC}"
    exit 1
fi

# If image path not provided, try to find image file
if [[ -z "$IMAGE_PATH" ]]; then
    # Try to find image file based on image name
    for ext in .png .jpg .jpeg; do
        candidate="$OUTPUT_REVERSED_DIR/../img/${IMAGE_NAME}${ext}"
        if [[ -f "$candidate" ]]; then
            IMAGE_PATH="$candidate"
            break
        fi
    done
    
    if [[ -z "$IMAGE_PATH" ]]; then
        # Try in current directory
        for ext in .png .jpg .jpeg; do
            candidate="./img/${IMAGE_NAME}${ext}"
            if [[ -f "$candidate" ]]; then
                IMAGE_PATH="$candidate"
                break
            fi
        done
    fi
    
    if [[ -z "$IMAGE_PATH" ]]; then
        echo -e "${YELLOW}⚠️  Warning: Image file not found for ${IMAGE_NAME}${NC}"
        echo "  Will use dummy path (Q&A generation may still work)"
        IMAGE_PATH="./img/${IMAGE_NAME}.png"
    fi
else
    # Validate that the provided image path exists
    if [[ ! -f "$IMAGE_PATH" ]]; then
        echo -e "${YELLOW}⚠️  Warning: Provided image path does not exist: $IMAGE_PATH${NC}"
        echo "  Will try to continue (Q&A generation may fail)"
    fi
fi

if [[ "$LLM_PROVIDER" != "claude" && "$LLM_PROVIDER" != "huggingface" ]]; then
    echo -e "${RED}❌ Error: LLM provider must be 'claude' or 'huggingface'${NC}"
    exit 1
fi

# Display configuration
echo -e "${YELLOW}📋 Configuration:${NC}"
echo "  Image Name: $IMAGE_NAME"
echo "  Image Path: $IMAGE_PATH"
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

# Ensure we use the conda environment's Python (same approach as knowledge extraction)
# Set PYTHONNOUSERSITE to prevent using user's local site-packages
export PYTHONNOUSERSITE=1

# Use python from conda environment explicitly (same as knowledge extraction script)
# Explicitly use conda's Python to avoid conflicts with system Python from module load
if [[ -n "$CONDA_PREFIX" ]]; then
    # Prioritize conda Python in PATH
    export PATH="$CONDA_PREFIX/bin:$PATH"
    export PYTHONPATH="$CONDA_PREFIX/lib/python3.11/site-packages:$PYTHONPATH"
    PYTHON_CMD="$CONDA_PREFIX/bin/python"
    PIP_CMD="$CONDA_PREFIX/bin/pip"
    echo "🔍 DEBUG: Using conda Python explicitly: $PYTHON_CMD"
    echo "🔍 DEBUG: Conda Python exists: $([ -f "$PYTHON_CMD" ] && echo 'YES' || echo 'NO')"
else
    PYTHON_CMD=$(which python)
    PIP_CMD=$(which pip)
    echo "🔍 DEBUG: CONDA_PREFIX not set, using: $PYTHON_CMD"
fi

echo "  Using Python: $PYTHON_CMD"
echo "  Python version: $($PYTHON_CMD --version 2>&1)"
echo "  Python executable check: $($PYTHON_CMD -c 'import sys; print(sys.executable)' 2>&1)"

# Check transformers in conda environment if using HuggingFace
if [[ "$LLM_PROVIDER" == "huggingface" ]]; then
    echo -e "${BLUE}📦 Checking transformers in conda environment...${NC}"
    
    # Check if transformers is accessible (same approach as knowledge extraction)
    echo "  Checking if transformers is already installed..."
    echo "  🔍 DEBUG: Using Python: $PYTHON_CMD"
    echo "  🔍 DEBUG: Python path: $($PYTHON_CMD -c 'import sys; print(sys.executable)' 2>&1)"
    SYS_PATH_DEBUG=$($PYTHON_CMD -c "import sys; print(':'.join(sys.path[:3]))" 2>&1)
    echo "  🔍 DEBUG: Python sys.path: $SYS_PATH_DEBUG"
    
    # Try to import transformers and capture any error
    TRANSFORMERS_CHECK=$($PYTHON_CMD -c "import transformers; print('OK')" 2>&1)
    if [[ "$TRANSFORMERS_CHECK" == "OK" ]]; then
        TRANSFORMERS_VERSION=$($PYTHON_CMD -c "import transformers; print(transformers.__version__)" 2>/dev/null)
        echo -e "${GREEN}  ✅ Transformers is already installed (version: $TRANSFORMERS_VERSION)${NC}"
        
        # Check if Qwen3-VL support is needed
        HUGGINGFACE_MODEL="${HUGGINGFACE_MODEL:-Qwen/Qwen3-VL-8B-Instruct}"
        if [[ "$HUGGINGFACE_MODEL" == *"Qwen3-VL"* ]]; then
            echo "  Checking Qwen3-VL support..."
            if $PYTHON_CMD -c "from transformers import Qwen3VLForConditionalGeneration" 2>/dev/null; then
                echo -e "${GREEN}  ✅ Qwen3-VL support is available${NC}"
            else
                echo -e "${YELLOW}  ⚠️  Qwen3-VL support not found, but will attempt to use existing transformers${NC}"
                echo -e "${YELLOW}  💡 If Q&A generation fails, run: bash scripts/sh/setup_conda_env.sh${NC}"
            fi
        fi
    else
        echo -e "${YELLOW}  ⚠️  Transformers not found in conda environment${NC}"
        echo "  🔍 DEBUG: Import error: $TRANSFORMERS_CHECK"
        echo "  🔍 DEBUG: Attempting to install transformers..."
        
        # Try to install transformers
        if $PIP_CMD install -q transformers torch 2>&1; then
            echo -e "${GREEN}  ✅ Transformers installed successfully${NC}"
        else
            echo -e "${RED}  ❌ Failed to install transformers${NC}"
            echo -e "${YELLOW}  💡 Please run setup script first: bash scripts/sh/setup_conda_env.sh${NC}"
            echo -e "${YELLOW}  💡 Or install manually: conda activate meme-qa-pipeline-env && pip install transformers torch${NC}"
            echo ""
            echo -e "${RED}❌ Error: transformers is required for HuggingFace provider${NC}"
            exit 1
        fi
    fi
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

# Use python from conda environment (same as knowledge extraction)
# PYTHONNOUSERSITE is already set above
# PYTHON_CMD is already set above with explicit conda path

echo -e "${BLUE}🐍 Using Python: $PYTHON_CMD${NC}"
echo -e "${BLUE}📍 Python version: $($PYTHON_CMD --version 2>&1)${NC}"
echo ""

# Verify transformers is accessible before running the script
if [[ "$LLM_PROVIDER" == "huggingface" ]]; then
    echo -e "${BLUE}🔍 Verifying transformers import...${NC}"
    if $PYTHON_CMD -c "import transformers; print(f'✅ Transformers {transformers.__version__} is accessible')" 2>&1; then
        echo ""
    else
        echo -e "${RED}❌ Error: transformers is not accessible in the Python environment${NC}"
        echo "  Python path: $PYTHON_CMD"
        echo "  Python version: $($PYTHON_CMD --version)"
        exit 1
    fi
fi

# Verify rdflib is accessible (needed for TTL extraction)
if [[ "$USE_TTL" == "true" ]]; then
    echo -e "${BLUE}🔍 Verifying rdflib import...${NC}"
    echo "  Using Python: $PYTHON_CMD"
    echo "  Python path: $(which python)"
    echo "  CONDA_PREFIX: $CONDA_PREFIX"
    if $PYTHON_CMD -c "import rdflib; print(f'✅ rdflib {rdflib.__version__} is accessible')" 2>&1; then
        echo ""
    else
        echo -e "${RED}❌ Error: rdflib is not accessible in the Python environment${NC}"
        echo "  Python path: $PYTHON_CMD"
        echo "  Please install rdflib: $PIP_CMD install rdflib"
        exit 1
    fi
fi

# Ensure PYTHON_CMD is an absolute path
if [[ ! "$PYTHON_CMD" =~ ^/ ]]; then
    PYTHON_CMD=$(which "$PYTHON_CMD" || echo "$PYTHON_CMD")
fi

echo -e "${BLUE}🐍 Final Python command: $PYTHON_CMD${NC}"
echo -e "${BLUE}🐍 Python version: $($PYTHON_CMD --version 2>&1)${NC}"

$PYTHON_CMD << 'PYTHON_SCRIPT'
import sys
import os
from pathlib import Path

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

# Convert to Path objects
image_path = Path(image_path_str) if image_path_str else None
dimensions_dir = Path(dimensions_dir_str) if dimensions_dir_str else None
output_dir = Path(output_dir_str) if output_dir_str else None

print(f'🖼️  Processing image: {image_name}')
print(f'📊 Dimensions directory: {dimensions_dir}')
print(f'💾 Output directory: {output_dir}')
print(f'🤖 LLM Provider: {llm_provider}')
print('')

# Determine TTL file path
if use_ttl:
    # Get TTL file path from environment or construct it
    ttl_file_str = os.environ.get('TTL_FILE', '')
    if ttl_file_str:
        ttl_file = Path(ttl_file_str)
    else:
        output_reversed_dir = Path(os.environ.get('OUTPUT_REVERSED_DIR', './output_reversed'))
        ttl_file = output_reversed_dir / f"{image_name}_enhanced_ontology_reversed.ttl"
    
    if not ttl_file.exists():
        print(f'❌ Error: TTL file not found: {ttl_file}')
        sys.exit(1)
    
    print(f'📄 Using TTL file: {ttl_file}')
    
    # Extract individuals from TTL file
    from scripts.py.extract_individuals_from_ttl import extract_individuals_by_dimension, create_jsonld_from_individual
    import tempfile
    import json
    
    print('📖 Extracting individuals from TTL file...')
    dimensions_by_class = extract_individuals_by_dimension(ttl_file)
    
    if not dimensions_by_class:
        print(f'❌ Error: No individuals found in TTL file')
        sys.exit(1)
    
    # Parse dimensions filter
    dimensions_filter = None
    if dimensions_filter_str:
        dimensions_filter = [d.strip() for d in dimensions_filter_str.split(',')]
        # Filter dimensions_by_class
        if dimensions_filter:
            dimensions_by_class = {k: v for k, v in dimensions_by_class.items() if k in dimensions_filter}
    
    print(f'📋 Found {len(dimensions_by_class)} dimension(s) with individuals')
    
    # Create temporary directory for JSON-LD files
    temp_dimensions_dir = Path(tempfile.mkdtemp(prefix='qa_ttl_'))
    print(f'📁 Creating temporary JSON-LD files in: {temp_dimensions_dir}')
    
    # Create JSON-LD files for each dimension and individual
    for dimension_name, individuals in dimensions_by_class.items():
        dimension_dir = temp_dimensions_dir / dimension_name
        dimension_dir.mkdir(parents=True, exist_ok=True)
        
        for individual in individuals:
            jsonld_data = create_jsonld_from_individual(individual, dimension_name, image_name)
            jsonld_file = dimension_dir / f"{image_name}_{individual['instance_name']}.jsonld"
            with open(jsonld_file, 'w', encoding='utf-8') as f:
                json.dump(jsonld_data, f, indent=2, ensure_ascii=False)
        
        print(f'  ✅ {dimension_name}: {len(individuals)} individual(s)')
    
    # Now use JSON-LD based Q&A generation with the temporary files
    from qa_generation_module import QAGenerationModule
    
    qa_module = QAGenerationModule(llm_provider=llm_provider)
    
    total_qa_pairs = 0
    dimensions_processed = []
    errors = []
    
    for dimension_name, individuals in dimensions_by_class.items():
        dimension_dir = temp_dimensions_dir / dimension_name
        dimension_files = list(dimension_dir.glob("*.jsonld"))
        
        if not dimension_files:
            warning = f"No JSON-LD files found for {dimension_name}"
            print(f'⚠️  {warning}')
            errors.append(warning)
            continue
        
        print(f'\\n📊 Processing {dimension_name} ({len(dimension_files)} file(s))')
        
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
    
    # Clean up temporary directory
    import shutil
    shutil.rmtree(temp_dimensions_dir)
    print(f'\\n🧹 Cleaned up temporary directory: {temp_dimensions_dir}')
    
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
else:
    # Use JSON-LD based Q&A generation with filtering
    from qa_generation_module import QAGenerationModule
    
    qa_module = QAGenerationModule(llm_provider=llm_provider)
    
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
        # Try with image name prefix first
        dimension_files = list(dimension_folder.glob(f"{image_name}_*.jsonld"))
        if not dimension_files:
            # Fallback to all files
            dimension_files = list(dimension_folder.glob("*.jsonld"))
        
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
            warning = f"No matching JSON-LD files found for {dimension_name}"
            print(f'⚠️  {warning}')
            errors.append(warning)
            continue
        
        print(f'\\n📊 Processing {dimension_name} ({len(dimension_files)} file(s))')
        
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

# Check if the Python script succeeded
if [[ $? -eq 0 ]]; then
    echo ""
    echo -e "${GREEN}🎉 Q&A generation pipeline completed successfully!${NC}"
    echo ""
    echo -e "${YELLOW}📁 Output files saved to: $OUTPUT_DIR${NC}"
    echo ""
    echo -e "${BLUE}📋 Generated files:${NC}"
    find "$OUTPUT_DIR" -name "*.jsonld" -o -name "*.txt" | head -10
    if [[ $(find "$OUTPUT_DIR" -name "*.jsonld" -o -name "*.txt" | wc -l) -gt 10 ]]; then
        echo "  ... and more files"
    fi
else
    echo ""
    echo -e "${RED}❌ Q&A generation pipeline failed!${NC}"
    exit 1
fi

