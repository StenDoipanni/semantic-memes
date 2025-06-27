#!/bin/bash

# Simple wrapper script for the Ollama Image Analyzer

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${GREEN}Ollama Image Analyzer${NC}"
echo "========================"

# Check if Python script exists
if [ ! -f "$SCRIPT_DIR/simple_image_analyzer.py" ]; then
    echo -e "${RED}Error: simple_image_analyzer.py not found${NC}"
    exit 1
fi

# Check if image file is provided
if [ $# -eq 0 ]; then
    echo -e "${YELLOW}No image specified, using default: batman-robin-global-warming.png${NC}"
    IMAGE_FILE="batman-robin-global-warming.png"
else
    IMAGE_FILE="$1"
fi

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

# Check if image file exists
if [ ! -f "$IMAGE_FILE" ]; then
    echo -e "${RED}Error: Image file '$IMAGE_FILE' not found${NC}"
    echo "Available images in img/:"
    PROJECT_ROOT="$(dirname "$(pwd)")"
    ls -1 "$PROJECT_ROOT/img"/*.png "$PROJECT_ROOT/img"/*.jpg "$PROJECT_ROOT/img"/*.jpeg "$PROJECT_ROOT/img"/*.gif "$PROJECT_ROOT/img"/*.bmp 2>/dev/null || echo "No image files found"
    exit 1
fi

# Run the analysis
echo -e "${GREEN}Analyzing: $IMAGE_FILE${NC}"
echo ""

python3 "$SCRIPT_DIR/simple_image_analyzer.py" "$IMAGE_FILE"

# Check exit status
if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}Analysis completed successfully!${NC}"
else
    echo -e "\n${RED}Analysis failed!${NC}"
    exit 1
fi 