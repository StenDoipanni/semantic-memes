#!/bin/bash

# Batch Image Analysis Script
# Processes multiple images using structured semiotic analysis
# Creates organized output folders for each image

# Activate conda environment
#source ~/miniconda3/etc/profile.d/conda.sh
#conda activate meme1-env

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Default config file
CONFIG_FILE="schemas/batch_config.json"

# Check if config file is provided
if [ $# -ge 1 ]; then
    CONFIG_FILE="$1"
fi

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: Config file '$CONFIG_FILE' not found."
    echo ""
    echo "Usage: $0 [config_file]"
    echo "Example: $0 schemas/batch_config.json"
    echo ""
    echo "Create a config file with this structure:"
    echo "{"
    echo "  \"default_fact_statement\": \"Default description\","
    echo "  \"images\": ["
    echo "    {"
    echo "      \"path\": \"image1.png\","
    echo "      \"fact_statement\": \"Description of image1\""
    echo "    },"
    echo "    {"
    echo "      \"path\": \"image2.png\","
    echo "      \"fact_statement\": \"Description of image2\""
    echo "    }"
    echo "  ]"
    echo "}"
    echo ""
    echo "Or copy batch_config_example.json and modify it."
    exit 1
fi

echo "=== Batch Semiotic Analysis ==="
echo "Config file: $CONFIG_FILE"
echo "Model: gemma3:12b"
echo "Framework: Greimas' Plastic Semiotics + PropBank Role - No Text Analysis"
echo "Output: Organized folder structure for each image"
echo "=================================="

# Run batch analysis
python "$SCRIPT_DIR/batch_semiotic_analyzer.py" "$CONFIG_FILE"

echo ""
echo "Batch analysis complete!"
echo "Check batch_summary.json for overall results." 