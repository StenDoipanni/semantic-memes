#!/usr/bin/env python3
"""
Test script for the Meme Analysis Pipeline.

This script tests the pipeline components and provides a quick way to verify
that everything is working correctly.
"""

import logging
import sys
from pathlib import Path

# Add the script directory to the path
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

from config import PipelineConfig, QAConfig
from ontology_loader import OntologyLoader
from llm_integration import LLMManager
from dimensions_extractor import DimensionsExtractor
from qa_generator import QAGenerator
from jsonld_handler import JSONLDHandler
from pipeline import MemeAnalysisPipeline

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_ontology_loader():
    """Test ontology loading functionality."""
    print("🧪 Testing Ontology Loader...")
    
    try:
        loader = OntologyLoader()
        
        # Test basic functionality
        metadata = loader.get_ontology_metadata()
        print(f"✅ Ontology loaded: {metadata['triple_count']} triples")
        
        # Test dimension classes extraction
        classes = loader.get_dimension_classes()
        print(f"✅ Dimension classes extracted: {len(classes)}")
        
        # Test validation
        issues = loader.validate_ontology()
        if issues:
            print(f"⚠️  Validation issues: {len(issues)}")
            for issue in issues[:3]:  # Show first 3 issues
                print(f"   - {issue}")
        else:
            print("✅ Ontology validation passed")
        
        return True
        
    except Exception as e:
        print(f"❌ Ontology loader test failed: {e}")
        return False


def test_llm_integration():
    """Test LLM integration functionality."""
    print("\n🧪 Testing LLM Integration...")
    
    try:
        manager = LLMManager()
        
        # Test provider availability
        providers = manager.get_available_providers()
        print(f"✅ Available providers: {providers}")
        
        if not providers:
            print("⚠️  No LLM providers available - check API keys and vLLM/HuggingFace setup")
            return False
        
        # Test simple prompt (without image)
        try:
            response = manager.generate_response("Hello, how are you?")
            print(f"✅ LLM response test successful: {response[:50]}...")
        except Exception as e:
            print(f"⚠️  LLM response test failed: {e}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ LLM integration test failed: {e}")
        return False


def test_jsonld_handler():
    """Test JSON-LD handler functionality."""
    print("\n🧪 Testing JSON-LD Handler...")
    
    try:
        handler = JSONLDHandler()
        
        # Test data
        test_dimensions = [
            {
                "class_name": "VisualMaterial",
                "instance_name": "test_element",
                "label": "the test element",
                "description": "A test element for validation"
            }
        ]
        
        test_qa = [
            {
                "question": "What is this?",
                "answer": "This is a test question and answer pair for validation purposes.",
                "question_type": "descriptive"
            }
        ]
        
        # Test dimensions JSON-LD creation
        image_path = Path("test_image.png")
        dimensions_doc = handler.create_dimensions_jsonld(test_dimensions, image_path)
        print("✅ Dimensions JSON-LD creation successful")
        
        # Test Q&A JSON-LD creation
        qa_doc = handler.create_qa_jsonld(test_qa, image_path)
        print("✅ Q&A JSON-LD creation successful")
        
        # Test unified JSON-LD creation
        unified_doc = handler.create_unified_jsonld(test_dimensions, test_qa, image_path)
        print("✅ Unified JSON-LD creation successful")
        
        # Test validation
        dim_issues = handler.validate_jsonld(dimensions_doc)
        qa_issues = handler.validate_jsonld(qa_doc)
        unified_issues = handler.validate_jsonld(unified_doc)
        
        total_issues = len(dim_issues) + len(qa_issues) + len(unified_issues)
        if total_issues == 0:
            print("✅ JSON-LD validation passed")
        else:
            print(f"⚠️  JSON-LD validation issues: {total_issues}")
        
        return True
        
    except Exception as e:
        print(f"❌ JSON-LD handler test failed: {e}")
        return False


def test_pipeline_components():
    """Test pipeline component initialization."""
    print("\n🧪 Testing Pipeline Components...")
    
    try:
        # Test dimensions extractor
        extractor = DimensionsExtractor()
        print(f"✅ Dimensions extractor initialized: {len(extractor.dimension_classes)} classes")
        
        # Test Q&A generator
        generator = QAGenerator()
        print("✅ Q&A generator initialized")
        
        # Test main pipeline
        pipeline = MemeAnalysisPipeline()
        status = pipeline.get_pipeline_status()
        print(f"✅ Pipeline initialized: {status['pipeline_ready']}")
        
        if status['pipeline_ready']:
            print("✅ All pipeline components ready")
        else:
            print("⚠️  Pipeline not fully ready - check configuration")
        
        return status['pipeline_ready']
        
    except Exception as e:
        print(f"❌ Pipeline components test failed: {e}")
        return False


def test_with_sample_image():
    """Test with the provided sample image."""
    print("\n🧪 Testing with Sample Image...")
    
    # Path to the provided meme image
    image_path = Path("/Users/stefanodegiorgis/Downloads/dev_set_task3_labeled/9_image_batch_2.png")
    
    if not image_path.exists():
        print(f"⚠️  Sample image not found: {image_path}")
        print("   Skipping image analysis test")
        return True
    
    try:
        # Test with minimal configuration
        pipeline = MemeAnalysisPipeline()
        
        result = pipeline.analyze_meme(
            image_path=image_path,
            selected_dimensions=["OverallIntent", "VisualMaterial"],  # Minimal set
            question_types=["descriptive"],  # Single question type
            questions_per_type=1,  # Single question
            save_outputs=False  # Don't save files during test
        )
        
        if result['success']:
            summary = result['summary']
            print(f"✅ Image analysis successful:")
            print(f"   - Dimensions extracted: {summary['dimensions_extracted']}")
            print(f"   - Q&A pairs generated: {summary['qa_pairs_generated']}")
            
            # Show sample results
            if result['dimensions']['dimensions']:
                dim = result['dimensions']['dimensions'][0]
                print(f"   - Sample dimension: {dim['class_name']} - {dim['label']}")
            
            if result['qa_generation']['success'] and result['qa_generation']['qa_pairs']:
                qa = result['qa_generation']['qa_pairs'][0]
                print(f"   - Sample Q&A: {qa['question'][:50]}...")
            
            return True
        else:
            print(f"❌ Image analysis failed: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Image analysis test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("🚀 Meme Analysis Pipeline - Test Suite")
    print("=" * 50)
    
    tests = [
        ("Ontology Loader", test_ontology_loader),
        ("LLM Integration", test_llm_integration),
        ("JSON-LD Handler", test_jsonld_handler),
        ("Pipeline Components", test_pipeline_components),
        ("Sample Image Analysis", test_with_sample_image)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Print summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} - {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Overall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All tests passed! Pipeline is ready to use.")
        return 0
    else:
        print("⚠️  Some tests failed. Check configuration and dependencies.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
