#!/usr/bin/env python3
"""
Simple Dimension Extraction Script.

This script directly runs dimension extraction without complex command-line parsing.
It sets up all the necessary environment variables and runs the extraction.
"""

import os
import sys
from pathlib import Path

# Set environment variables
os.environ['CLAUDE_API_KEY'] = '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'
os.environ['ONTOLOGY_PATH'] = '/home/sdegiorgis/memes/meme-pipeline-server/memes-features/meme-dimensions.ttl'
os.environ['PROMPTS_DIR'] = '/home/sdegiorgis/memes/meme-pipeline-server/memes-features/prompts/dimension-extraction-prompts'

# Add current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

def main():
    """Run dimension extraction with the specified parameters."""
    
    print("🚀 Simple Dimension Extraction")
    print("=" * 40)
    
    # Configuration
    image_path = Path("/Users/stefanodegiorgis/Downloads/dev_set_task3_labeled/9_image_batch_2.png")
    selected_dimensions = ["TextualMaterial", "VisualMaterial", "SceneUnderstanding", "BackgroundKnowledge"]
    output_dir = Path("./output/simple_extraction")
    llm_provider = "claude"
    
    print(f"📁 Image: {image_path}")
    print(f"📊 Dimensions: {selected_dimensions}")
    print(f"📁 Output: {output_dir}")
    print(f"🤖 LLM Provider: {llm_provider}")
    print("")
    
    # Check if image exists
    if not image_path.exists():
        print(f"❌ Image not found: {image_path}")
        return 1
    
    try:
        # Import and run the dimension extraction module
        from dimension_extraction_module import extract_dimensions_from_image
        
        print("🔍 Starting dimension extraction...")
        result = extract_dimensions_from_image(
            image_path=image_path,
            selected_dimensions=selected_dimensions,
            output_dir=output_dir,
            llm_provider=llm_provider
        )
        
        # Print results
        if result['success']:
            print("\n✅ Dimension extraction completed successfully!")
            print(f"📊 Dimensions extracted: {result['metadata']['total_dimensions_found']}")
            print(f"🔍 Dimensions processed: {', '.join(result['metadata']['dimensions_processed'])}")
            
            # Show extracted dimensions
            print("\n📋 Extracted Dimensions:")
            for i, dim in enumerate(result['dimensions'], 1):
                print(f"  {i}. {dim['class_name']}: {dim['label']}")
                print(f"     Description: {dim['description']}")
                print(f"     Confidence: {dim.get('confidence', 'N/A')}")
                print("")
            
            # Show saved files
            if result.get('saved_files'):
                print("📁 Output files:")
                for file_type, file_path in result['saved_files'].items():
                    print(f"  - {file_type}: {file_path}")
            
            return 0
        else:
            print(f"\n❌ Dimension extraction failed: {result.get('error', 'Unknown error')}")
            return 1
            
    except Exception as e:
        print(f"\n❌ Error during extraction: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
