#!/usr/bin/env python3
"""
Command-line tool for extracting specific dimensions from meme images.

This script allows you to specify exactly which dimensions you want to extract
from the command line.

Usage:
    python extract_dimensions.py <image_path> --dimensions VisualMaterial TextualMaterial Emotion
    
    python extract_dimensions.py <image_path> --dimensions Emotion --output-dir ./output
"""

import argparse
import sys
from pathlib import Path
from typing import List, Optional

# Add current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from dimension_extraction_module import extract_dimensions_from_image

# Available dimensions (from config)
AVAILABLE_DIMENSIONS = [
    "VisualMaterial",
    "TextualMaterial",
    "Emotion",
    "ColorComposition",
    "Scene",
    "BackgroundKnowledge",
    "Metadata",
    "AnalogicalMapping",
    "OverallIntent",
    "SemioticProjection",
    "TargetCommunity",
    "TemplateStructure",
    "Toxicity"
]


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Extract specific dimensions from meme images",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
  # Extract specific dimensions
  python extract_dimensions.py image.png --dimensions VisualMaterial TextualMaterial
  
  # Extract single dimension
  python extract_dimensions.py image.png --dimensions Emotion
  
  # Extract with custom output directory
  python extract_dimensions.py image.png --dimensions Scene BackgroundKnowledge --output-dir ./my_output
  
  # Use specific LLM provider
  python extract_dimensions.py image.png --dimensions VisualMaterial --llm-provider claude

Available dimensions:
  {', '.join(AVAILABLE_DIMENSIONS)}
        """
    )
    
    parser.add_argument(
        "image_path",
        type=Path,
        help="Path to the meme image file"
    )
    
    parser.add_argument(
        "--dimensions",
        nargs="+",
        choices=AVAILABLE_DIMENSIONS,
        required=True,
        help="List of dimensions to extract (space-separated)"
    )
    
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory for results (default: ./output)"
    )
    
    parser.add_argument(
        "--llm-provider",
        choices=["claude", "huggingface"],
        default="claude",
        help="LLM provider to use (default: claude)"
    )
    
    parser.add_argument(
        "--list-dimensions",
        action="store_true",
        help="List all available dimensions and exit"
    )
    
    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_arguments()
    
    # List dimensions and exit if requested
    if args.list_dimensions:
        print("Available dimensions:")
        for i, dim in enumerate(AVAILABLE_DIMENSIONS, 1):
            print(f"  {i}. {dim}")
        return 0
    
    # Validate image path
    image_path = args.image_path
    if not image_path.exists():
        print(f"❌ Error: Image file not found: {image_path}")
        return 1
    
    # Validate dimensions
    if not args.dimensions:
        print("❌ Error: At least one dimension must be specified")
        print(f"Available dimensions: {', '.join(AVAILABLE_DIMENSIONS)}")
        return 1
    
    # Print configuration
    print("🚀 Dimension Extraction")
    print("=" * 60)
    print(f"📁 Image: {image_path}")
    print(f"📊 Dimensions: {', '.join(args.dimensions)}")
    print(f"🤖 LLM Provider: {args.llm_provider}")
    if args.output_dir:
        print(f"📁 Output Directory: {args.output_dir}")
    print("=" * 60)
    print()
    
    try:
        # Run extraction
        print("🔍 Starting dimension extraction...")
        result = extract_dimensions_from_image(
            image_path=image_path,
            selected_dimensions=args.dimensions,
            output_dir=args.output_dir,
            llm_provider=args.llm_provider
        )
        
        # Print results
        if result['success']:
            print("\n✅ Dimension extraction completed successfully!")
            print(f"📊 Total dimensions extracted: {result['metadata']['total_dimensions_found']}")
            print(f"🔍 Dimensions processed: {', '.join(result['metadata']['dimensions_processed'])}")
            
            # Show summary of extracted dimensions
            if result.get('dimensions'):
                print("\n📋 Extracted Dimensions Summary:")
                dimension_counts = {}
                for dim in result['dimensions']:
                    class_name = dim.get('class_name', 'Unknown')
                    dimension_counts[class_name] = dimension_counts.get(class_name, 0) + 1
                
                for dim_name, count in sorted(dimension_counts.items()):
                    print(f"  • {dim_name}: {count} instance(s)")
            
            # Show saved files
            if result.get('saved_files'):
                print("\n📁 Output files saved:")
                for file_type, file_path in result['saved_files'].items():
                    if isinstance(file_path, list):
                        if file_type.endswith("_individual"):
                            dimension_name = file_type.replace("_individual", "")
                            print(f"  - {file_type}: {len(file_path)} files in dimensions/{dimension_name}/")
                            # Show first few files
                            for fp in file_path[:3]:
                                print(f"    • {fp}")
                            if len(file_path) > 3:
                                print(f"    • ... and {len(file_path) - 3} more")
                        else:
                            print(f"  - {file_type}: {len(file_path)} files")
                    else:
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



