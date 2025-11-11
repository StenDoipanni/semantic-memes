"""
Example Usage Script for Meme Analysis Pipeline.

This script demonstrates how to use the meme analysis pipeline with different
configurations and provides examples of common use cases.
"""

import logging
from pathlib import Path
from typing import List, Dict, Any

from pipeline import MemeAnalysisPipeline, analyze_meme, batch_analyze_memes
from config import PipelineConfig, QAConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def example_single_meme_analysis():
    """Example: Analyze a single meme image."""
    print("=== Single Meme Analysis Example ===")
    
    # Path to the meme image
    image_path = Path("/Users/stefanodegiorgis/Downloads/dev_set_task3_labeled/9_image_batch_2.png")
    
    if not image_path.exists():
        print(f"Image not found: {image_path}")
        return
    
    # Analyze the meme
    result = analyze_meme(
        image_path=image_path,
        selected_dimensions=["OverallIntent", "VisualMaterial", "TextualMaterial"],
        question_types=["descriptive", "interpretive", "analytical"],
        questions_per_type=2,
        llm_provider="claude",  # or "huggingface" or None for auto-selection
        output_dir=Path("output/example_single"),
        save_outputs=True
    )
    
    # Print results
    print(f"Analysis successful: {result['success']}")
    if result['success']:
        summary = result['summary']
        print(f"Dimensions extracted: {summary['dimensions_extracted']}")
        print(f"Q&A pairs generated: {summary['qa_pairs_generated']}")
        print(f"Files saved: {summary['files_saved']}")
        
        # Show some extracted dimensions
        print("\nExtracted Dimensions:")
        for dim in result['dimensions']['dimensions'][:3]:  # Show first 3
            print(f"- {dim['class_name']}: {dim['label']}")
        
        # Show some Q&A pairs
        if result['qa_generation']['success']:
            print("\nGenerated Q&A Pairs:")
            for qa in result['qa_generation']['qa_pairs'][:2]:  # Show first 2
                print(f"Q: {qa['question']}")
                print(f"A: {qa['answer'][:100]}...")
                print()


def example_batch_analysis():
    """Example: Analyze multiple meme images in batch."""
    print("=== Batch Analysis Example ===")
    
    # List of meme images to analyze
    image_paths = [
        Path("/Users/stefanodegiorgis/Downloads/dev_set_task3_labeled/9_image_batch_2.png"),
        # Add more image paths here
    ]
    
    # Filter existing images
    existing_paths = [p for p in image_paths if p.exists()]
    
    if not existing_paths:
        print("No valid images found for batch analysis")
        return
    
    # Analyze all images
    results = batch_analyze_memes(
        image_paths=existing_paths,
        selected_dimensions=["OverallIntent", "VisualMaterial"],
        question_types=["descriptive"],
        questions_per_type=1,
        llm_provider=None,  # Auto-select best available provider
        output_dir=Path("output/example_batch"),
        save_outputs=True
    )
    
    # Print batch results
    successful = sum(1 for r in results if r['success'])
    print(f"Batch analysis completed: {successful}/{len(results)} successful")
    
    for i, result in enumerate(results):
        if result['success']:
            print(f"Image {i+1}: {result['summary']['dimensions_extracted']} dimensions, "
                  f"{result['summary']['qa_pairs_generated']} Q&A pairs")
        else:
            print(f"Image {i+1}: Failed - {result.get('error', 'Unknown error')}")


def example_custom_pipeline():
    """Example: Using the pipeline class directly with custom configuration."""
    print("=== Custom Pipeline Example ===")
    
    # Create custom pipeline instance
    pipeline = MemeAnalysisPipeline(
        llm_provider="claude",
        output_dir=Path("output/example_custom")
    )
    
    # Check pipeline status
    status = pipeline.get_pipeline_status()
    print("Pipeline Status:")
    print(f"- Ontology loaded: {status['ontology_loaded']}")
    print(f"- Available LLM providers: {status['llm_providers_available']}")
    print(f"- Dimension classes available: {status['dimension_classes_available']}")
    print(f"- Pipeline ready: {status['pipeline_ready']}")
    
    if not status['pipeline_ready']:
        print("Pipeline not ready. Check configuration.")
        return
    
    # Analyze with custom settings
    image_path = Path("/Users/stefanodegiorgis/Downloads/dev_set_task3_labeled/9_image_batch_2.png")
    
    if image_path.exists():
        result = pipeline.analyze_meme(
            image_path=image_path,
            selected_dimensions=["OverallIntent", "Emotion", "ColorComposition"],
            question_types=["interpretive", "evaluative"],
            questions_per_type=3,
            save_outputs=True
        )
        
        print(f"Custom analysis successful: {result['success']}")
        if result['success']:
            print(f"Unified output created: {result['unified_output']['success']}")


def example_dimension_specific_analysis():
    """Example: Focus on specific dimensions only."""
    print("=== Dimension-Specific Analysis Example ===")
    
    image_path = Path("/Users/stefanodegiorgis/Downloads/dev_set_task3_labeled/9_image_batch_2.png")
    
    if not image_path.exists():
        print(f"Image not found: {image_path}")
        return
    
    # Focus only on visual and textual dimensions
    result = analyze_meme(
        image_path=image_path,
        selected_dimensions=["VisualMaterial", "TextualMaterial"],
        question_types=["descriptive"],
        questions_per_type=3,
        output_dir=Path("output/example_visual_textual"),
        save_outputs=True
    )
    
    if result['success']:
        print("Visual and Textual Analysis Results:")
        for dim in result['dimensions']['dimensions']:
            print(f"- {dim['class_name']}: {dim['description']}")


def example_qa_focused_analysis():
    """Example: Focus on Q&A generation with different question types."""
    print("=== Q&A-Focused Analysis Example ===")
    
    image_path = Path("/Users/stefanodegiorgis/Downloads/dev_set_task3_labeled/9_image_batch_2.png")
    
    if not image_path.exists():
        print(f"Image not found: {image_path}")
        return
    
    # Generate comprehensive Q&A
    result = analyze_meme(
        image_path=image_path,
        selected_dimensions=None,  # Use all available dimensions
        question_types=["descriptive", "analytical", "interpretive", "contextual", "evaluative"],
        questions_per_type=2,
        output_dir=Path("output/example_comprehensive_qa"),
        save_outputs=True
    )
    
    if result['success'] and result['qa_generation']['success']:
        print("Comprehensive Q&A Results:")
        
        # Group Q&A by type
        qa_by_type = {}
        for qa in result['qa_generation']['qa_pairs']:
            qa_type = qa['question_type']
            if qa_type not in qa_by_type:
                qa_by_type[qa_type] = []
            qa_by_type[qa_type].append(qa)
        
        # Print Q&A by type
        for qa_type, qa_list in qa_by_type.items():
            print(f"\n{qa_type.upper()} Questions:")
            for qa in qa_list:
                print(f"Q: {qa['question']}")
                print(f"A: {qa['answer'][:150]}...")
                print()


def example_error_handling():
    """Example: Demonstrating error handling."""
    print("=== Error Handling Example ===")
    
    # Test with non-existent image
    result = analyze_meme(
        image_path=Path("non_existent_image.png"),
        output_dir=Path("output/example_errors")
    )
    
    print(f"Non-existent image result: {result['success']}")
    if not result['success']:
        print(f"Error: {result.get('error', 'Unknown error')}")
    
    # Test with invalid image format
    try:
        result = analyze_meme(
            image_path=Path("test.txt"),  # Wrong format
            output_dir=Path("output/example_errors")
        )
    except Exception as e:
        print(f"Invalid format error caught: {e}")


def main():
    """Run all examples."""
    print("Meme Analysis Pipeline - Example Usage")
    print("=" * 50)
    
    try:
        # Run examples
        example_single_meme_analysis()
        print("\n" + "=" * 50)
        
        example_batch_analysis()
        print("\n" + "=" * 50)
        
        example_custom_pipeline()
        print("\n" + "=" * 50)
        
        example_dimension_specific_analysis()
        print("\n" + "=" * 50)
        
        example_qa_focused_analysis()
        print("\n" + "=" * 50)
        
        example_error_handling()
        
    except Exception as e:
        logger.error(f"Example execution failed: {e}")
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
