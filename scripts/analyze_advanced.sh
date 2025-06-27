#!/bin/bash

# Structured Entailment Trees Analysis - Step 1
# This script runs the structured semiotic analysis with PropBank roles and text analysis

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Structured Entailment Trees Analysis - Step 1${NC}"
echo -e "${BLUE}============================================${NC}"

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Activate conda environment
echo -e "${YELLOW}Activating conda environment: meme1-env${NC}"
source ~/anaconda3/etc/profile.d/conda.sh
conda activate meme1-env

# Check if Python script exists
if [ ! -f "$SCRIPT_DIR/advanced_semiotic_analyzer.py" ]; then
    echo -e "${RED}Error: advanced_semiotic_analyzer.py not found${NC}"
    exit 1
fi

# Check if prompt template exists
if [ ! -f "$SCRIPT_DIR/../prompts/structured_semiotic_prompt.txt" ]; then
    echo -e "${RED}Error: structured_semiotic_prompt.txt not found${NC}"
    exit 1
fi

# Default parameters
DEFAULT_IMAGE="batman-robin-global-warming.png"
DEFAULT_FACT="Batman slapping Robin"

# Get parameters from command line or use defaults
IMAGE_FILE="${1:-$DEFAULT_IMAGE}"
FACT_STATEMENT="${2:-$DEFAULT_FACT}"
OUTPUT_FORMAT="${3:-}"

# If IMAGE_FILE is just a filename, prepend img/ relative to project root
if [[ "$IMAGE_FILE" != */* ]]; then
    # Check if we're in the scripts directory or root directory
    if [[ "$(basename "$(pwd)")" == "scripts" ]]; then
        # We're in scripts/, so go up one level to get project root
        PROJECT_ROOT="$(dirname "$(pwd)")"
    else
        # We're in the project root
        PROJECT_ROOT="$(pwd)"
    fi
    IMAGE_FILE="$PROJECT_ROOT/img/$IMAGE_FILE"
fi

# Determine output format
if [[ "$OUTPUT_FORMAT" == "--json-ld" ]]; then
    OUTPUT_DESC="JSON-LD with semantic web structure"
    PYTHON_ARGS="$IMAGE_FILE $FACT_STATEMENT --json-ld"
else
    OUTPUT_DESC="Structured JSON with organized folder"
    PYTHON_ARGS="$IMAGE_FILE $FACT_STATEMENT"
fi

echo -e "${GREEN}Image: $IMAGE_FILE${NC}"
echo -e "${GREEN}Fact Statement: $FACT_STATEMENT${NC}"
echo -e "${GREEN}Model: gemma3:12b${NC}"
echo -e "${GREEN}Step: Structured Semiotic Description (Greimas' Plastic Semiotics)${NC}"
echo -e "${GREEN}Output: $OUTPUT_DESC${NC}"
echo ""

# Run the analysis
python "$SCRIPT_DIR/advanced_semiotic_analyzer.py" $PYTHON_ARGS

# Check exit status
if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}✅ Structured analysis completed successfully!${NC}"
    if [[ "$OUTPUT_FORMAT" == "--json-ld" ]]; then
        echo -e "${YELLOW}📁 Results saved to: outputs/structured_entailment_analysis_*_step1_semiotics_*.json${NC}"
    else
        echo -e "${YELLOW}📁 Results saved to: outputs/analysis_*/${NC}"
    fi
    echo -e "${BLUE}🔄 Ready for Step 2: Fact Extraction from structured data${NC}"
    echo -e "${BLUE}📊 JSON-LD format ready for knowledge base construction${NC}"
    echo -e "${BLUE}🎯 PropBank roles: COM, LOC, DIR, GOL, MNR, TMP, EXT, PRP, CAU, MOD, NEG, ADV${NC}"
    echo -e "${BLUE}📝 Text analysis: 12 relation types for text-image mapping${NC}"
else
    echo -e "\n${RED}❌ Structured analysis failed!${NC}"
    exit 1
fi 