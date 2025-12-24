#!/usr/bin/env python3
"""
Script to process TTL knowledge graph files and transform them into named graphs
with meme_object and assertion entities.

The script:
1. Converts TTL files to N-triples
2. Transforms all URIs by adding an image_id prefix (../[image_id]/)
3. Creates a meme_object_[image_id] individual of MemeObject class
4. Creates an assertion_about_[image_id] individual
5. Connects meme_object to assertion with hasAssertion property
6. Connects assertion to all individuals with relatedTo property
"""

import os
import re
import sys
from pathlib import Path
from rdflib import Graph, URIRef, Namespace, Literal
from rdflib.namespace import RDF, RDFS, OWL, XSD
from urllib.parse import urlparse, urlunparse
from typing import Set, List


# Base namespace - using w3c.org namespace
BASE_NS = Namespace("http://w3c.org/memes-ontology/general#")
MEME_NS = Namespace("http://w3c.org/memes-ontology/general#")


def extract_image_id(filename: str) -> str:
    """Extract image_id from filename like '01235_refined_ontology.ttl' or '01235_enhanced_ontology_reversed.ttl'."""
    match = re.match(r'^(\d+)_', filename)
    if match:
        return match.group(1)
    raise ValueError(f"Could not extract image_id from filename: {filename}")


def transform_uri(uri: str, image_id: str) -> str:
    """
    Transform a URI by:
    1. Changing namespace from example.org to w3c.org
    2. Adding image_id to the base URI path (before the #)
    
    Only transforms URIs from the base namespace (http://w3c.org/memes-ontology/general#)
    or the old example.org namespace (for backwards compatibility).
    Standard RDF/OWL/RDFS URIs are not transformed.
    
    For example: 
    - http://example.org/multimodal-taxonomy#man -> http://w3c.org/memes-ontology/general/01235#man
    - http://w3c.org/memes-ontology/general#man -> http://w3c.org/memes-ontology/general/01235#man
    
    This creates named graphs where each image has its own graph URI.
    """
    # Don't transform standard RDF/OWL/RDFS namespaces
    standard_namespaces = [
        "http://www.w3.org/1999/02/22-rdf-syntax-ns",
        "http://www.w3.org/2000/01/rdf-schema",
        "http://www.w3.org/2002/07/owl",
        "http://www.w3.org/2001/XMLSchema",
        "http://www.w3.org/XML/1998/namespace"
    ]
    
    # Check if URI belongs to a standard namespace
    for ns in standard_namespaces:
        if uri.startswith(ns):
            return uri  # Don't transform standard namespaces
    
    # Replace example.org namespace with w3c.org namespace
    if uri.startswith("http://example.org/multimodal-taxonomy"):
        uri = uri.replace("http://example.org/multimodal-taxonomy", "http://w3c.org/memes-ontology/general")
    
    # Handle fragment-based URIs (e.g., http://w3c.org/memes-ontology/general#man)
    if '#' in uri:
        base, fragment = uri.rsplit('#', 1)
        # Insert image_id in the base path, before the #
        # e.g., http://w3c.org/memes-ontology/general#man -> http://w3c.org/memes-ontology/general/01235#man
        if base.endswith('#'):
            base = base.rstrip('#')
        new_uri = f"{base}/{image_id}#{fragment}"
    else:
        # Handle path-based URIs
        parsed = urlparse(uri)
        path = parsed.path.rstrip('/')
        if path:
            new_path = f"{path}/{image_id}"
        else:
            new_path = f"/{image_id}"
        new_uri = urlunparse((
            parsed.scheme,
            parsed.netloc,
            new_path,
            parsed.params,
            parsed.query,
            parsed.fragment
        ))
    
    return new_uri


def get_all_individuals(graph: Graph) -> Set[URIRef]:
    """Extract all individual URIs from the graph (excluding classes and properties)."""
    individuals = set()
    
    # First, identify what are classes, properties, and ontology
    classes = set()
    properties = set()
    ontologies = set()
    
    # Standard RDF/OWL types that indicate metadata, not individuals
    standard_types = {
        OWL.Class, OWL.ObjectProperty, OWL.DatatypeProperty, 
        OWL.AnnotationProperty, OWL.Ontology, RDFS.Class
    }
    
    for s, p, o in graph:
        if p == RDF.type:
            if o in standard_types:
                if isinstance(s, URIRef):
                    if o == OWL.Class:
                        classes.add(s)
                    elif o in [OWL.ObjectProperty, OWL.DatatypeProperty, OWL.AnnotationProperty]:
                        properties.add(s)
                    elif o == OWL.Ontology:
                        ontologies.add(s)
    
    # Now find all individuals: subjects that have rdf:type pointing to a class (not OWL.Class itself)
    for s, p, o in graph:
        if p == RDF.type and isinstance(s, URIRef):
            # Skip if it's a class, property, or ontology definition
            if s not in classes and s not in properties and s not in ontologies:
                # If o is not a standard type, it's likely an individual
                if o not in standard_types:
                    individuals.add(s)
    
    return individuals


def process_ttl_file(input_file: Path, output_dir: Path) -> None:
    """
    Process a single TTL file:
    1. Load and convert to N-triples
    2. Transform URIs with image_id prefix
    3. Add meme_object and assertion entities
    4. Write output as N-triples
    """
    print(f"Processing: {input_file.name}")
    
    # Extract image_id from filename
    image_id = extract_image_id(input_file.name)
    print(f"  Image ID: {image_id}")
    
    # Load the TTL file
    g = Graph()
    g.parse(str(input_file), format='turtle')
    
    # Create a new graph for the transformed data
    transformed_g = Graph()
    
    # First, identify classes, properties, and ontology in the original graph
    classes = set()
    properties = set()
    ontologies = set()
    
    standard_types = {
        OWL.Class, OWL.ObjectProperty, OWL.DatatypeProperty, 
        OWL.AnnotationProperty, OWL.Ontology, RDFS.Class
    }
    
    for s, p, o in g:
        if p == RDF.type:
            if o in standard_types:
                if isinstance(s, URIRef):
                    if o == OWL.Class:
                        classes.add(s)
                    elif o in [OWL.ObjectProperty, OWL.DatatypeProperty, OWL.AnnotationProperty]:
                        properties.add(s)
                    elif o == OWL.Ontology:
                        ontologies.add(s)
    
    # Get all individuals before transformation
    original_individuals = get_all_individuals(g)
    
    # Transform triples - only transform individual URIs, not classes or properties
    for s, p, o in g:
        # Transform subject URI only if it's an individual (not a class, property, or ontology)
        if isinstance(s, URIRef):
            if s in original_individuals:
                new_s = URIRef(transform_uri(str(s), image_id))
            else:
                new_s = s  # Keep classes, properties, and ontology URIs unchanged
        else:
            new_s = s
        
        # Never transform predicate URIs - they should stay as in the main ontology
        new_p = p
        
        # Transform object URI only if it's an individual (not a class or property)
        if isinstance(o, URIRef):
            # Check if it's an individual (not a class or property)
            if o in original_individuals:
                new_o = URIRef(transform_uri(str(o), image_id))
            elif o in classes or o in properties or o in ontologies:
                new_o = o  # Keep classes and properties unchanged
            else:
                # For objects that are not clearly identified, check if they're used as types
                # If p is rdf:type, then o is likely a class, so don't transform
                if p == RDF.type:
                    new_o = o  # Keep class references unchanged
                elif o in original_individuals:
                    new_o = URIRef(transform_uri(str(o), image_id))
                else:
                    new_o = o  # Conservative: don't transform if uncertain
        else:
            new_o = o
        
        # Add the transformed triple
        transformed_g.add((new_s, new_p, new_o))
    
    # Use original ontology classes and properties (not transformed)
    meme_object_class = URIRef(f"{BASE_NS}MemeObject")
    has_assertion_prop = URIRef(f"{BASE_NS}hasAssertion")
    asserts_prop = URIRef(f"{MEME_NS}asserts")
    
    # Create URIs for new entities (these are individuals, so they should be transformed)
    meme_object_uri = URIRef(transform_uri(f"{BASE_NS}meme_object_{image_id}", image_id))
    assertion_uri = URIRef(transform_uri(f"{BASE_NS}assertion_about_{image_id}", image_id))
    
    # Create meme_object individual (using original MemeObject class)
    transformed_g.add((meme_object_uri, RDF.type, meme_object_class))
    transformed_g.add((meme_object_uri, RDFS.label, Literal(f"meme_object_{image_id}", lang="en")))
    
    # Create assertion individual
    transformed_g.add((assertion_uri, RDFS.label, Literal(f"assertion_about_{image_id}", lang="en")))
    
    # Connect meme_object to assertion (using original hasAssertion property)
    transformed_g.add((meme_object_uri, has_assertion_prop, assertion_uri))
    
    # Get all transformed individuals (excluding the new ones we just created)
    transformed_individuals = get_all_individuals(transformed_g)
    # Remove the new entities we just created
    transformed_individuals.discard(meme_object_uri)
    transformed_individuals.discard(assertion_uri)
    
    # Connect assertion to all individuals with asserts (not relatedTo)
    print(f"  Connecting assertion to {len(transformed_individuals)} individuals using asserts")
    for individual in transformed_individuals:
        transformed_g.add((assertion_uri, asserts_prop, individual))
    
    # Add toxicity-related triples
    # Define property URIs
    has_toxicity_value_prop = URIRef(f"{BASE_NS}hasToxicityValue")
    has_toxicity_type_prop = URIRef(f"{BASE_NS}hasToxicityType")
    has_toxicity_explanation_prop = URIRef(f"{BASE_NS}hasToxicityExplanation")
    
    # Find Toxicity class URIs (check both old and new namespaces)
    toxicity_class_old = URIRef("http://example.org/multimodal-taxonomy#ToxicityAssessment")
    toxicity_class_new = URIRef(f"{BASE_NS}ToxicityAssessment")
    toxicity_class_alt = URIRef("http://example.org/multimodal-taxonomy#Toxicity")
    
    # Find all Toxicity individuals in the transformed graph
    toxicity_individuals = []
    for s, p, o in transformed_g:
        if p == RDF.type:
            if o in [toxicity_class_old, toxicity_class_new, toxicity_class_alt]:
                toxicity_individuals.append(s)
    
    if toxicity_individuals:
        # At least one Toxicity individual found
        print(f"  Found {len(toxicity_individuals)} Toxicity individual(s)")
        
        # Use the first toxicity individual for type and explanation
        toxicity_individual = toxicity_individuals[0]
        
        # Add hasToxicityValue = true
        transformed_g.add((assertion_uri, has_toxicity_value_prop, Literal(True, datatype=XSD.boolean)))
        
        # Get the label (rdfs:label) of the toxicity individual
        toxicity_label = None
        for s, p, o in transformed_g:
            if s == toxicity_individual and p == RDFS.label:
                if isinstance(o, Literal):
                    toxicity_label = str(o)
                    break
        
        # Get the comment (rdfs:comment) of the toxicity individual
        toxicity_comment = None
        for s, p, o in transformed_g:
            if s == toxicity_individual and p == RDFS.comment:
                if isinstance(o, Literal):
                    toxicity_comment = str(o)
                    break
        
        # Add hasToxicityType with the label
        if toxicity_label:
            transformed_g.add((assertion_uri, has_toxicity_type_prop, Literal(toxicity_label, lang="en")))
        else:
            # Fallback: use a default or the URI fragment
            label_fallback = str(toxicity_individual).split('#')[-1] if '#' in str(toxicity_individual) else str(toxicity_individual)
            transformed_g.add((assertion_uri, has_toxicity_type_prop, Literal(label_fallback, lang="en")))
        
        # Add hasToxicityExplanation with the comment
        if toxicity_comment:
            transformed_g.add((assertion_uri, has_toxicity_explanation_prop, Literal(toxicity_comment, lang="en")))
        else:
            # Fallback: empty string or default message
            transformed_g.add((assertion_uri, has_toxicity_explanation_prop, Literal("Toxicity detected but no explanation available", lang="en")))
    else:
        # No Toxicity individual found
        print(f"  No Toxicity individuals found, adding hasToxicityValue = false")
        transformed_g.add((assertion_uri, has_toxicity_value_prop, Literal(False, datatype=XSD.boolean)))
    
    # Write output as N-triples
    output_file = output_dir / f"{image_id}_transformed.nt"
    transformed_g.serialize(destination=str(output_file), format='nt', encoding='utf-8')
    print(f"  Output written to: {output_file}")
    print(f"  Total triples: {len(transformed_g)}\n")


def main():
    """Main function to process all TTL files in a directory."""
    if len(sys.argv) < 2:
        print("Usage: python process_graphs.py <input_directory> [output_directory]")
        print("  input_directory: Directory containing TTL files")
        print("  output_directory: Directory for output N-triples files (default: input_directory/transformed)")
        sys.exit(1)
    
    input_dir = Path(sys.argv[1])
    if not input_dir.exists():
        print(f"Error: Input directory does not exist: {input_dir}")
        sys.exit(1)
    
    if len(sys.argv) >= 3:
        output_dir = Path(sys.argv[2])
    else:
        output_dir = input_dir / "transformed"
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Find all TTL files (try both patterns)
    ttl_files = list(input_dir.glob("*_refined_ontology.ttl"))
    if not ttl_files:
        ttl_files = list(input_dir.glob("*_enhanced_ontology_reversed.ttl"))
    
    if not ttl_files:
        print(f"No TTL files found in {input_dir}")
        print("Looking for files matching pattern: *_refined_ontology.ttl or *_enhanced_ontology_reversed.ttl")
        sys.exit(1)
    
    print(f"Found {len(ttl_files)} TTL files to process\n")
    
    # Create a combined graph for all_graphs.nt
    combined_graph = Graph()
    
    # Process each file
    for ttl_file in sorted(ttl_files):
        try:
            # Process the file and get the output path
            process_ttl_file(ttl_file, output_dir)
            
            # Read the generated .nt file and add to combined graph
            output_file = output_dir / f"{extract_image_id(ttl_file.name)}_transformed.nt"
            if output_file.exists():
                temp_g = Graph()
                temp_g.parse(str(output_file), format='nt')
                # Add all triples from this file to the combined graph
                for triple in temp_g:
                    combined_graph.add(triple)
                    
        except Exception as e:
            print(f"Error processing {ttl_file.name}: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    # Write the combined graph
    combined_output = output_dir / "all_graphs.nt"
    combined_graph.serialize(destination=str(combined_output), format='nt', encoding='utf-8')
    print(f"\nCombined graph written to: {combined_output}")
    print(f"  Total triples in combined graph: {len(combined_graph)}")
    
    print(f"\nProcessing complete! Output files written to: {output_dir}")


if __name__ == "__main__":
    main()

