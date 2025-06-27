#!/bin/bash

# Basic Entailment Trees Analysis - Step 1 (Simple Version)
# This script runs the basic semiotic analysis with JSON-LD output
# For structured analysis with PropBank roles, use run_structured_entailment.sh

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Basic Entailment Trees Analysis - Step 1 (Simple Version)${NC}"
echo -e "${BLUE}=====================================================${NC}"

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Activate conda environment
echo -e "${YELLOW}Activating conda environment: meme1-env${NC}"
source ~/anaconda3/etc/profile.d/conda.sh
conda activate meme1-env

# Check if Python script exists
if [ ! -f "$SCRIPT_DIR/basic_semiotic_analyzer.py" ]; then
    echo -e "${RED}Error: basic_semiotic_analyzer.py not found${NC}"
    exit 1
fi

# Default parameters
DEFAULT_IMAGE="batman-robin-global-warming.png"
DEFAULT_FACT="Batman slapping Robin"

# Get parameters from command line or use defaults
IMAGE_FILE="${1:-$DEFAULT_IMAGE}"
FACT_STATEMENT="${2:-$DEFAULT_FACT}"

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

echo -e "${GREEN}Image: $IMAGE_FILE${NC}"
echo -e "${GREEN}Fact Statement: $FACT_STATEMENT${NC}"
echo -e "${GREEN}Model: gemma3:12b${NC}"
echo -e "${GREEN}Step: Basic Semiotic Description (Greimas' Plastic Semiotics)${NC}"
echo -e "${GREEN}Output: Simple JSON-LD format${NC}"
echo -e "${YELLOW}Note: For structured analysis with PropBank roles, use run_structured_entailment.sh${NC}"
echo ""

# Run the analysis
python "$SCRIPT_DIR/basic_semiotic_analyzer.py" "$IMAGE_FILE" "$FACT_STATEMENT"

# Check exit status
if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}✅ Basic analysis completed successfully!${NC}"
    echo -e "${YELLOW}📁 Results saved to: outputs/entailment_analysis_*_step1_semiotics.json${NC}"
    echo -e "${BLUE}🔄 Ready for Step 2: Fact Extraction from basic data${NC}"
    echo -e "${BLUE}📊 JSON-LD format ready for knowledge base construction${NC}"
    echo -e "${YELLOW}💡 For advanced analysis with PropBank roles, try: run_structured_entailment.sh${NC}"
else
    echo -e "\n${RED}❌ Basic analysis failed!${NC}"
    exit 1
fi 