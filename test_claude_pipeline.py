#!/usr/bin/env python3
"""
Test script for the Meme Analysis Pipeline with Claude API.
"""

import os
import sys
from pathlib import Path

# Add the script directory to the path
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

# Set environment variables
os.environ['ONTOLOGY_PATH'] = '/home/sdegiorgis/memes/meme-pipeline-server/memes-features/meme-dimensions.ttl'
os.environ['PROMPTS_DIR'] = '/home/sdegiorgis/memes/meme-pipeline-server/memes-features/prompts/dimension-extraction-prompts'

from config import LLMConfig, OntologyConfig
from llm_integration import LLMManager
from ontology_loader import OntologyLoader

def test_claude_connection():
    """Test Claude API connection."""
    print("🤖 Testing Claude API connection...")
    
    # Check if API key is set
    if not LLMConfig.CLAUDE_API_KEY:
        print("❌ Claude API key not set. Please set CLAUDE_API_KEY environment variable.")
        return False
    
    print(f"✅ Claude API key found")
    print(f"✅ Using model: {LLMConfig.CLAUDE_MODEL}")
    
    # Test LLM manager
    llm_manager = LLMManager()
    
    available_providers = llm_manager.get_available_providers()
    if 'claude' in available_providers:
        print("✅ Claude provider is available")
        
        # Test a simple prompt
        try:
            response = llm_manager.generate_response(
                "Hello! Please respond with just 'Hello from Claude Haiku!' to confirm the connection is working.",
                provider='claude'
            )
            print(f"✅ Claude response: {response}")
            return True
        except Exception as e:
            print(f"❌ Claude API test failed: {e}")
            return False
    else:
        print("❌ Claude provider is not available")
        return False

def test_ontology_loading():
    """Test ontology loading."""
    print("\n📚 Testing ontology loading...")
    
    try:
        loader = OntologyLoader()
        metadata = loader.get_ontology_metadata()
        print(f"✅ Ontology loaded: {metadata['triple_count']} triples")
        
        classes = loader.get_dimension_classes()
        print(f"✅ Dimension classes: {len(classes)}")
        
        return True
    except Exception as e:
        print(f"❌ Ontology loading failed: {e}")
        return False

def test_pipeline_components():
    """Test pipeline components."""
    print("\n🔧 Testing pipeline components...")
    
    try:
        from dimensions_extractor import DimensionsExtractor
        from qa_generator import QAGenerator
        from jsonld_handler import JSONLDHandler
        
        print("✅ All pipeline components imported successfully")
        return True
    except Exception as e:
        print(f"❌ Pipeline components test failed: {e}")
        return False

def main():
    """Main test function."""
    print("🚀 Meme Pipeline - Claude API Test")
    print("==================================")
    
    # Test Claude connection
    claude_ok = test_claude_connection()
    
    # Test ontology loading
    ontology_ok = test_ontology_loading()
    
    # Test pipeline components
    components_ok = test_pipeline_components()
    
    print("\n📊 Test Results:")
    print(f"  Claude API: {'✅ PASS' if claude_ok else '❌ FAIL'}")
    print(f"  Ontology: {'✅ PASS' if ontology_ok else '❌ FAIL'}")
    print(f"  Components: {'✅ PASS' if components_ok else '❌ FAIL'}")
    
    if claude_ok and ontology_ok and components_ok:
        print("\n🎉 All tests passed! Pipeline is ready for use.")
        return True
    else:
        print("\n⚠️  Some tests failed. Check the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
