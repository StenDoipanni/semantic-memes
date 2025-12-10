#!/usr/bin/env python3
"""
Extract individuals from TTL file grouped by dimension.

This script extracts all individuals from a TTL ontology file and groups them by dimension class.
"""

import sys
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


def extract_individuals_by_dimension(ttl_file: Path) -> Dict[str, List[Dict[str, Any]]]:
    """
    Extract individuals from TTL file grouped by dimension class.
    
    Args:
        ttl_file: Path to the TTL file
        
    Returns:
        Dictionary mapping dimension class names to lists of individual dictionaries
    """
    dimensions_by_class = {}
    
    try:
        # Load the TTL file
        g = rdflib.Graph()
        g.parse(ttl_file, format="turtle")
        
        # Define namespaces
        EX = Namespace("http://example.org/multimodal-taxonomy#")
        RDFS = Namespace("http://www.w3.org/2000/01/rdf-schema#")
        RDF = Namespace("http://www.w3.org/1999/02/22-rdf-syntax-ns#")
        
        # All possible dimension classes (updated list)
        dimension_classes = [
            "TextualMaterial", "VisualMaterial", "EmotionExpression",
            "ColorComposition", "Scene", "BackgroundKnowledge",
            "Metadata", "AnalogicalMapping", "OverallIntent",
            "SemioticProjection", "TargetCommunity", "TemplateStructure",
            "ToxicityAssessment", "MetaphoricalAndAnalogicalMapping", "SceneUnderstanding"
        ]
        
        processed_instances = set()
        
        # Iterate through all triples to find dimension instances
        for subject, predicate, obj in g.triples((None, None, None)):
            if (isinstance(subject, rdflib.URIRef) and 
                str(subject).startswith("http://example.org/multimodal-taxonomy#") and
                subject not in processed_instances):
                
                # Get the class type
                class_type = None
                for _, _, class_obj in g.triples((subject, RDF.type, None)):
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
                        individual = {
                            "instance_name": instance_name,
                            "label": label,
                            "description": description,
                            "extraction_method": extraction_method or "unknown"
                        }
                        
                        # Group by dimension class
                        if class_type not in dimensions_by_class:
                            dimensions_by_class[class_type] = []
                        dimensions_by_class[class_type].append(individual)
        
        return dimensions_by_class
        
    except Exception as e:
        print(f"Error extracting individuals from TTL file: {e}", file=sys.stderr)
        return {}


def create_jsonld_from_individual(individual: Dict[str, Any], dimension_name: str, image_name: str) -> Dict[str, Any]:
    """Create a JSON-LD structure from an individual."""
    return {
        "@context": {
            "@vocab": "http://example.org/multimodal-taxonomy#",
            "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
            "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
            "owl": "http://www.w3.org/2002/07/owl#"
        },
        "@id": f"http://example.org/multimodal-taxonomy#{individual['instance_name']}",
        "@type": dimension_name,
        "instance_name": individual["instance_name"],
        "label": individual["label"],
        "description": individual["description"],
        "extractionMethod": individual["extraction_method"]
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extract_individuals_from_ttl.py <ttl_file>", file=sys.stderr)
        sys.exit(1)
    
    ttl_file = Path(sys.argv[1])
    if not ttl_file.exists():
        print(f"Error: TTL file not found: {ttl_file}", file=sys.stderr)
        sys.exit(1)
    
    # Extract individuals grouped by dimension
    dimensions_by_class = extract_individuals_by_dimension(ttl_file)
    
    # Output as JSON
    print(json.dumps(dimensions_by_class, indent=2, ensure_ascii=False))



