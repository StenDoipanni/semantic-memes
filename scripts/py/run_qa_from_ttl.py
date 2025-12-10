#!/usr/bin/env python3
"""
Script to generate Q&A pairs from TTL ontology files.

This script loads a TTL file, extracts dimension data, and generates Q&A pairs.
"""

import sys
import argparse
import logging
import json
from pathlib import Path
from typing import Dict, List, Any
import rdflib
from rdflib import Namespace, Literal

# Ensure repository root is on sys.path
CURRENT_FILE = Path(__file__).resolve()
REPO_ROOT = CURRENT_FILE.parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Set up environment variables BEFORE importing modules
import os
if not os.getenv("CLAUDE_API_KEY"):
    os.environ["CLAUDE_API_KEY"] = "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"

# Set HuggingFace environment variables if needed
if not os.getenv("HUGGINGFACE_MODEL"):
    os.environ["HUGGINGFACE_MODEL"] = "Qwen/Qwen2-VL-7B-Instruct"

from qa_generation_module import QAGenerationModule, generate_qa_for_image
from config import QAConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_dimensions_from_ttl(ttl_file: Path) -> List[Dict[str, Any]]:
    """
    Extract dimension data from a TTL ontology file.
    
    Args:
        ttl_file: Path to the TTL file
        
    Returns:
        List of dimension dictionaries
    """
    dimensions = []
    
    try:
        # Load the TTL file
        g = rdflib.Graph()
        g.parse(ttl_file, format="turtle")
        
        # Define namespaces
        EX = Namespace("http://example.org/multimodal-taxonomy#")
        RDFS = Namespace("http://www.w3.org/2000/01/rdf-schema#")
        
        # Find all dimension instances (only those with proper class types)
        dimension_classes = [
            "TextualMaterial", "VisualMaterial", "Emotion", 
            "ColorComposition", "Scene", "BackgroundKnowledge",
            "Metadata", "AnalogicalMapping", "OverallIntent",
            "SemioticProjection", "TargetCommunity", "TemplateStructure",
            "Toxicity"
        ]
        
        processed_instances = set()
        
        for subject, predicate, obj in g.triples((None, None, None)):
            if (isinstance(subject, rdflib.URIRef) and 
                str(subject).startswith("http://example.org/multimodal-taxonomy#") and
                subject not in processed_instances):
                
                # Get the class type first
                class_type = None
                for _, _, class_obj in g.triples((subject, rdflib.RDF.type, None)):
                    if isinstance(class_obj, rdflib.URIRef):
                        potential_class = class_obj.split("#")[-1]
                        if potential_class in dimension_classes:
                            class_type = potential_class
                            break
                
                # Only process if it's a valid dimension class
                if class_type:
                    processed_instances.add(subject)
                    instance_name = subject.split("#")[-1]
                    
                    # Get label
                    label = None
                    for _, _, label_obj in g.triples((subject, RDFS.label, None)):
                        if isinstance(label_obj, Literal):
                            label = str(label_obj)
                            break
                    
                    # Get description
                    description = None
                    for _, _, desc_obj in g.triples((subject, RDFS.comment, None)):
                        if isinstance(desc_obj, Literal):
                            description = str(desc_obj)
                            break
                    
                    # Get extraction method
                    extraction_method = None
                    for _, _, method_obj in g.triples((subject, EX.extractionMethod, None)):
                        if isinstance(method_obj, Literal):
                            extraction_method = str(method_obj)
                            break
                    
                    if class_type and label and description:
                        dimension = {
                            "class_name": class_type,
                            "instance_name": instance_name,
                            "label": label,
                            "description": description,
                            "extraction_method": extraction_method or "unknown"
                        }
                        dimensions.append(dimension)
                        logger.info(f"Extracted dimension: {class_type} - {label}")
        
        logger.info(f"Extracted {len(dimensions)} dimensions from TTL file")
        return dimensions
        
    except Exception as e:
        logger.error(f"Failed to extract dimensions from TTL file: {e}")
        return []

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate Q&A pairs from TTL ontology files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate Q&A from a TTL file
  python run_qa_from_ttl.py output/sea_monkeys_enhanced_ontology.ttl

  # Generate specific question types
  python run_qa_from_ttl.py output/sea_monkeys_enhanced_ontology.ttl --question-types descriptive interpretive

  # Generate more questions per type
  python run_qa_from_ttl.py output/sea_monkeys_enhanced_ontology.ttl --questions-per-type 3

  # Use specific LLM provider
  python run_qa_from_ttl.py output/sea_monkeys_enhanced_ontology.ttl --llm-provider claude
        """
    )
    
    parser.add_argument(
        "ttl_file",
        type=Path,
        help="Path to the TTL ontology file"
    )
    
    parser.add_argument(
        "--question-types",
        nargs="*",
        choices=QAConfig.QUESTION_TYPES,
        help="Types of questions to generate (default: all types)"
    )
    
    parser.add_argument(
        "--questions-per-type",
        type=int,
        default=QAConfig.QUESTIONS_PER_TYPE,
        help=f"Number of questions per type (default: {QAConfig.QUESTIONS_PER_TYPE})"
    )
    
    parser.add_argument(
        "--llm-provider",
        choices=["claude", "huggingface"],
        help="LLM provider to use (default: auto-select)"
    )
    
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output"),
        help="Output directory for results (default: output)"
    )
    
    parser.add_argument(
        "--image-path",
        type=Path,
        help="Explicit path to the image file (if not provided, will try to find from TTL filename)"
    )
    
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validate TTL file
    if not args.ttl_file.exists():
        logger.error(f"TTL file not found: {args.ttl_file}")
        sys.exit(1)
    
    print("🔍 Q&A Generation from TTL File")
    print("=" * 40)
    print(f"📁 TTL File: {args.ttl_file}")
    print(f"❓ Question Types: {args.question_types or 'All available'}")
    print(f"🔢 Questions per Type: {args.questions_per_type}")
    print(f"🤖 LLM Provider: {args.llm_provider or 'Auto-select'}")
    print(f"📁 Output Directory: {args.output_dir}")
    print("=" * 40)
    
    # Extract dimensions from TTL file
    print("📖 Extracting dimensions from TTL file...")
    dimensions = extract_dimensions_from_ttl(args.ttl_file)
    
    if not dimensions:
        logger.error("No dimensions found in TTL file")
        sys.exit(1)
    
    print(f"✅ Extracted {len(dimensions)} dimensions")
    
    # Determine image path
    if args.image_path:
        # Use explicitly provided image path
        image_path = args.image_path.resolve()
        if not image_path.exists():
            logger.error(f"Image file not found: {image_path}")
            sys.exit(1)
        image_name = image_path.stem
        logger.info(f"Using provided image path: {image_path}")
    else:
        # Try to find image from TTL filename
        # Extract base name from TTL filename, handling various naming patterns
        image_name = args.ttl_file.stem
        
        # Remove all common suffixes that might be in TTL filenames
        suffixes_to_remove = [
            "_enhanced_ontology_reversed", "_enhanced_ontology_claude_haiku", "_enhanced_ontology_claude4", 
            "_enhanced_ontology_llama", "_enhanced_ontology", "_claude_haiku", "_claude4", "_llama"
        ]
        
        for suffix in suffixes_to_remove:
            if image_name.endswith(suffix):
                image_name = image_name.replace(suffix, "")
                break
        
        # Try to find the actual image file
        possible_extensions = [".png", ".jpg", ".jpeg"]
        image_path = None
        
        # Try multiple locations
        search_paths = [
            Path(f"img/{image_name}"),
            Path(f"./img/{image_name}"),
            Path(f"../img/{image_name}"),
        ]
        
        for base_path in search_paths:
            for ext in possible_extensions:
                candidate_path = base_path.with_suffix(ext)
                if candidate_path.exists():
                    image_path = candidate_path.resolve()
                    break
            if image_path:
                break
        
        # If no image found, create a path and warn
        if not image_path:
            image_path = Path(f"img/{image_name}.png")
            logger.warning(f"Image file not found, using path: {image_path}")
            logger.warning("Q&A generation may fail if image is required by the LLM")
    
    # Create dimension files structure for qa_generation_module
    print("📁 Creating dimension files structure...")
    dimensions_dir = args.output_dir / "dimensions"
    dimensions_dir.mkdir(parents=True, exist_ok=True)
    
    # Group dimensions by class_name and create JSON-LD files
    dimension_groups = {}
    for dim in dimensions:
        class_name = dim["class_name"]
        if class_name not in dimension_groups:
            dimension_groups[class_name] = []
        dimension_groups[class_name].append(dim)
    
    # Create JSON-LD files for each dimension group
    for class_name, dims in dimension_groups.items():
        class_dir = dimensions_dir / class_name
        class_dir.mkdir(parents=True, exist_ok=True)
        
        for i, dim in enumerate(dims):
            jsonld_file = class_dir / f"{image_name}_{dim['instance_name']}.jsonld"
            jsonld_data = {
                "@context": {
                    "@vocab": "http://example.org/multimodal-taxonomy#"
                },
                "@id": f"http://example.org/multimodal-taxonomy#{dim['instance_name']}",
                "@type": class_name,
                "instance_name": dim["instance_name"],
                "label": dim["label"],
                "description": dim["description"],
                "extraction_method": dim.get("extraction_method", "unknown")
            }
            
            with open(jsonld_file, 'w', encoding='utf-8') as f:
                json.dump(jsonld_data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Created {len(dimension_groups)} dimension groups with JSON-LD files")
    
    # Generate Q&A pairs using the proper module
    print("🤖 Generating Q&A pairs...")
    qa_module = QAGenerationModule(llm_provider=args.llm_provider or "claude")
    
    results = generate_qa_for_image(
        image_path=image_path,
        dimensions_dir=dimensions_dir,
        output_dir=args.output_dir,
        llm_provider=args.llm_provider or "claude"
    )
    
    if results["success"]:
        print(f"✅ Generated Q&A pairs for {len(results['dimensions_processed'])} dimensions")
        print(f"📊 Total Q&A pairs: {results['total_qa_pairs']}")
        
        if results["errors"]:
            print(f"⚠️  Errors: {len(results['errors'])}")
            for error in results["errors"]:
                print(f"  - {error}")
        
        print(f"📁 Results saved to: {args.output_dir}")
        print("📝 Check the qa/ subdirectory for individual Q&A files")
            
    else:
        logger.error(f"Q&A generation failed: {results.get('error', 'Unknown error')}")
        sys.exit(1)

if __name__ == "__main__":
    main()
