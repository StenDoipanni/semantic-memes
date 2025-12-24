#!/usr/bin/env python3
"""
Command-line tool for extracting dimensions from meme images using the reversed pipeline.

This script uses the reversed extraction order that starts with OverallIntent,
then extracts: TextualMaterial, VisualMaterial, Scene, BackgroundKnowledge,
AnalogicalMapping, and ToxicityAssessment.

Usage:
    python extract_dimensions_reversed.py <image_path> [--llm-provider claude|huggingface] [--output-dir ./output]
"""

import argparse
import sys
from pathlib import Path
from typing import List, Optional

# Add current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from reversed_dimension_extraction_module import extract_dimensions_from_image_reversed

# Default dimensions for reversed pipeline
REVERSED_PIPELINE_DIMENSIONS = [
    "OverallIntent",
    "TextualMaterial",
    "VisualMaterial",
    "Scene",
    "BackgroundKnowledge",
    "EmotionExpression",
    "AnalogicalMapping",
    "SemioticProjection",
    "ToxicityAssessment",
    "TargetCommunity"
]


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Extract dimensions from meme images using reversed pipeline (starts with OverallIntent)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
  # Extract with default reversed pipeline dimensions
  python extract_dimensions_reversed.py image.png
  
  # Extract with custom output directory
  python extract_dimensions_reversed.py image.png --output-dir ./my_output
  
  # Use specific LLM provider
  python extract_dimensions_reversed.py image.png --llm-provider claude
  
  # Extract with custom dimensions (still in reversed order)
  python extract_dimensions_reversed.py image.png --dimensions ToxicityAssessment TextualMaterial VisualMaterial

Default reversed pipeline dimensions:
  {', '.join(REVERSED_PIPELINE_DIMENSIONS)}
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
        default=None,
        help=f"List of dimensions to extract in reversed order (default: {', '.join(REVERSED_PIPELINE_DIMENSIONS)})"
    )
    
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory for results (default: ./output_reversed)"
    )
    
    parser.add_argument(
        "--llm-provider",
        choices=["claude", "huggingface"],
        default="claude",
        help="LLM provider to use (default: claude)"
    )
    
    parser.add_argument(
        "--additional-kb",
        type=Path,
        nargs="+",
        default=None,
        help="Path(s) to additional knowledge base file(s) (JSON-LD format) to include in prompts. Can specify multiple files."
    )
    
    parser.add_argument(
        "--iterative-kb",
        type=str,
        choices=["true", "false"],
        default="false",
        help="If 'true', attach additional KB to all prompts, not just OverallIntent (default: false)"
    )
    
    parser.add_argument(
        "--refine",
        type=str,
        choices=["true", "false"],
        default="false",
        help="If 'true', run refinement step after extraction to add relations between individuals (default: false)"
    )
    
    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_arguments()
    
    # Validate image path
    image_path = args.image_path
    if not image_path.exists():
        print(f"❌ Error: Image file not found: {image_path}")
        return 1
    
    # Use default dimensions if not specified
    dimensions = args.dimensions if args.dimensions else REVERSED_PIPELINE_DIMENSIONS
    
    # Set default output directory
    output_dir = args.output_dir or Path("./output_reversed")
    
    # Print configuration
    print("🚀 Reversed Dimension Extraction Pipeline")
    print("=" * 70)
    print(f"📁 Image: {image_path}")
    print(f"📊 Extraction Order:")
    print(f"   1. OverallIntent (first - graph passed to all subsequent steps)")
    print(f"   2. TextualMaterial (receives OverallIntent graph as context)")
    print(f"   3. VisualMaterial (receives OverallIntent graph as context)")
    print(f"   4. Scene (receives OverallIntent graph + VisualMaterial entities)")
    print(f"   5. BackgroundKnowledge (receives OverallIntent graph + VisualMaterial, TextualMaterial, Scene entities)")
    print(f"   6. EmotionExpression (receives OverallIntent graph + VisualMaterial, TextualMaterial, Scene, BackgroundKnowledge entities)")
    print(f"   7. AnalogicalMapping (receives OverallIntent graph + VisualMaterial, TextualMaterial, Scene, BackgroundKnowledge, EmotionExpression entities)")
    print(f"   8. SemioticProjection (receives OverallIntent graph + VisualMaterial, TextualMaterial, Scene, BackgroundKnowledge, AnalogicalMapping entities)")
    print(f"   9. ToxicityAssessment (receives OverallIntent graph + VisualMaterial, TextualMaterial, Scene, BackgroundKnowledge, EmotionExpression, AnalogicalMapping, SemioticProjection entities)")
    print(f"  10. TargetCommunity (receives OverallIntent graph + VisualMaterial, TextualMaterial, Scene, BackgroundKnowledge, AnalogicalMapping, ToxicityAssessment entities)")
    print(f"🤖 LLM Provider: {args.llm_provider}")
    print(f"📁 Output Directory: {output_dir}")
    print("=" * 70)
    print()
    
    try:
        # Run extraction
        print("🔍 Starting reversed dimension extraction...")
        print("   Step 1: Extracting OverallIntent (no dependencies)")
        print("   Step 2-7: Extracting supporting dimensions with context from OverallIntent")
        print()
        
        # Convert iterative_kb string to boolean
        iterative_kb = args.iterative_kb.lower() == "true" if args.iterative_kb else False
        
        result = extract_dimensions_from_image_reversed(
            image_path=image_path,
            selected_dimensions=dimensions,
            output_dir=output_dir,
            llm_provider=args.llm_provider,
            additional_kb_paths=args.additional_kb,
            iterative_kb=iterative_kb
        )
        
        # Run refinement if requested
        refine_enabled = args.refine.lower() == "true" if args.refine else False
        if refine_enabled and result['success']:
            print("\n" + "=" * 70)
            print("🔧 Running Refinement Step")
            print("=" * 70)
            
            # Find the generated TTL file
            image_name = image_path.stem
            
            # Check saved_files first (most reliable)
            ttl_file = None
            if result.get('saved_files') and 'enhanced_ttl' in result['saved_files']:
                ttl_file = Path(result['saved_files']['enhanced_ttl'])
            
            # If not found, try common naming patterns
            if not ttl_file or not ttl_file.exists():
                possible_names = [
                    f"{image_name}_enhanced_ontology_reversed.ttl",
                    f"{image_name}_enhanced_ontology.ttl",
                ]
                for name in possible_names:
                    candidate = output_dir / name
                    if candidate.exists():
                        ttl_file = candidate
                        break
            
            # Last resort: look for any TTL file matching the image name
            if not ttl_file or not ttl_file.exists():
                ttl_files = list(output_dir.glob(f"{image_name}*.ttl"))
                if ttl_files:
                    # Prefer files with "enhanced" in the name
                    enhanced_files = [f for f in ttl_files if "enhanced" in f.name]
                    ttl_file = enhanced_files[0] if enhanced_files else ttl_files[0]
            
            if ttl_file and ttl_file.exists():
                from refinement_module import RefinementModule
                
                refinement_module = RefinementModule(llm_provider=args.llm_provider)
                refined_output = output_dir / f"{image_name}_refined_ontology.ttl"
                
                refinement_result = refinement_module.refine_ontology(
                    ttl_file=ttl_file,
                    image_path=image_path,
                    output_path=refined_output
                )
                
                if refinement_result['success']:
                    print(f"✅ Refinement completed successfully!")
                    print(f"📊 Total triples added: {refinement_result['total_triples_added']}")
                    print(f"📁 Refined ontology saved to: {refined_output}")
                    for mat_result in refinement_result.get('materializer_results', []):
                        status = "✅" if mat_result['success'] else "❌"
                        print(f"  {status} {mat_result['materializer']}: {mat_result.get('triples_added', 0)} triples")
                else:
                    print(f"⚠️  Refinement failed: {refinement_result.get('error', 'Unknown error')}")
            else:
                print(f"⚠️  Could not find generated TTL file for refinement")
                print(f"   Looked for: {output_dir / f'{image_name}_enhanced_ontology.ttl'}")
        
        # Print results
        if result['success']:
            print("\n✅ Reversed dimension extraction completed successfully!")
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
            print(f"\n❌ Reversed dimension extraction failed: {result.get('error', 'Unknown error')}")
            return 1
            
    except Exception as e:
        print(f"\n❌ Error during extraction: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

