#!/bin/bash
# Activation script for meme-qa-pipeline-env

echo "🚀 Activating meme-qa-pipeline-env environment..."
echo "=================================================="

# Activate conda environment
source ~/miniconda3/etc/profile.d/conda.sh
conda activate meme-qa-pipeline-env

# Set environment variables
# API key should be set via environment variable or .env file
# Do not hardcode API keys in version control
# export CLAUDE_API_KEY="${CLAUDE_API_KEY:-}"
export ONTOLOGY_PATH="/home/sdegiorgis/memes/meme-pipeline-server/memes-features/meme-dimensions.ttl"
export PROMPTS_DIR="/home/sdegiorgis/memes/meme-pipeline-server/prompts/dimension-extraction-prompts"
export OUTPUT_DIR="/home/sdegiorgis/memes/meme-pipeline-server/output"

echo "✅ Environment activated: meme-qa-pipeline-env"
echo "✅ Python version: $(python --version)"
echo "✅ Claude API key: Set"
echo "✅ Ontology path: $ONTOLOGY_PATH"
echo "✅ Prompts dir: $PROMPTS_DIR"
echo "✅ Output dir: $OUTPUT_DIR"
echo ""
echo "🎯 Ready to run the pipeline!"
echo ""
echo "📋 Usage Examples:"
echo "  # Core dimensions (4): TextualMaterial, VisualMaterial, Scene, BackgroundKnowledge"
echo "  python run_pipeline.py 9_image_batch_2.png --mode dimension_extraction --dimensions TextualMaterial VisualMaterial Scene BackgroundKnowledge --llm-provider claude"
echo ""
echo "  # All dimensions (13): All available dimensions"
echo "  python run_pipeline.py 9_image_batch_2.png --mode dimension_extraction --dimensions TextualMaterial VisualMaterial Emotion ColorComposition Scene BackgroundKnowledge Metadata AnalogicalMapping OverallIntent SemioticProjection TargetCommunity TemplateStructure Toxicity --llm-provider claude"
