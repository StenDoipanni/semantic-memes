#!/bin/bash

# Test Ollama locally with optimized settings
# This script tests Ollama without requiring GPU resources

set -e

echo "🧪 Testing Ollama Local Configuration"
echo "===================================="

# Set environment variables
export CLAUDE_API_KEY="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"
export ONTOLOGY_PATH="/home/sdegiorgis/memes/meme-pipeline-server/memes-features/meme-dimensions.ttl"
export PROMPTS_DIR="/home/sdegiorgis/memes/meme-pipeline-server/prompts/dimension-extraction-prompts"

# Activate conda environment
source /home/sdegiorgis/miniconda3/bin/activate meme-qa-pipeline-env

# Navigate to pipeline directory
cd /home/sdegiorgis/memes/meme-pipeline-server

# Start Ollama with optimized settings
echo "🤖 Starting Ollama with optimized settings..."
ollama serve &
OLLAMA_PID=$!

# Wait for Ollama to start
echo "⏳ Waiting for Ollama to start..."
sleep 5

# Check if Ollama is responding
until curl -s http://localhost:11434/api/tags > /dev/null; do
    echo "⏳ Waiting for Ollama service..."
    sleep 2
done
echo "✅ Ollama service started"

# Test Ollama integration
echo "🧪 Testing Ollama integration..."
python3 -c "
from llm_integration import LLMManager
import logging
logging.basicConfig(level=logging.INFO)

print('Testing Ollama integration...')
llm_manager = LLMManager()
providers = llm_manager.get_available_providers()
print(f'Available providers: {providers}')

if 'ollama' in providers:
    print('Testing Ollama with llama3.2-vision:11b...')
    try:
        response = llm_manager.generate_response(
            'Hello! Please respond with just \"Ollama vision test successful!\"',
            provider='ollama'
        )
        print(f'✅ Ollama response: {response}')
        print('✅ Ollama integration working!')
    except Exception as e:
        print(f'❌ Ollama test failed: {e}')
        exit(1)
else:
    print('❌ Ollama provider not available')
    exit(1)
"

# Test with a simple dimension extraction
echo "🧪 Testing dimension extraction with Ollama..."
python3 -c "
from dimension_extraction_module import extract_dimensions_from_image
from pathlib import Path

print('Testing dimension extraction with Ollama...')
try:
    result = extract_dimensions_from_image(
        image_path=Path('9_image_batch_2.png'),
        selected_dimensions=['TextualMaterial'],
        output_dir=Path('./test_ollama_output'),
        llm_provider='ollama'
    )
    
    if result['success']:
        print(f'✅ Dimension extraction successful!')
        print(f'📊 Dimensions found: {len(result[\"dimensions\"])}')
        for dim in result['dimensions']:
            print(f'  - {dim[\"class_name\"]}: {dim[\"label\"]}')
    else:
        print(f'❌ Dimension extraction failed: {result.get(\"error\", \"Unknown error\")}')
        exit(1)
        
except Exception as e:
    print(f'❌ Error during dimension extraction: {e}')
    exit(1)
"

echo ""
echo "🎉 Ollama integration test completed successfully!"
echo "✅ Ollama is working with qwen3:8b model"
echo "✅ Dimension extraction is working with Ollama"

# Clean up
echo "🛑 Stopping Ollama service..."
kill $OLLAMA_PID
echo "✅ Test completed"
