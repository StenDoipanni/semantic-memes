"""
Ontology Loader and Parser Module.

This module handles loading, parsing, and querying OWL ontology files in Turtle format.
It provides functionality to extract classes, properties, and their annotations for use
in the meme analysis pipeline.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from rdflib import Graph, URIRef, Literal, Namespace
from rdflib.namespace import RDF, RDFS, OWL

from config import OntologyConfig, ErrorMessages

logger = logging.getLogger(__name__)


class OntologyLoader:
    """
    Handles loading and parsing of OWL ontology files.
    
    This class provides methods to load ontology files, extract classes and properties,
    and retrieve specific information needed for dimension extraction.
    """
    
    def __init__(self, ontology_path: Optional[Path] = None):
        """
        Initialize the ontology loader.
        
        Args:
            ontology_path: Path to the ontology file. If None, uses default from config.
        """
        self.ontology_path = ontology_path or OntologyConfig.ONTOLOGY_PATH
        self.graph = Graph()
        self.namespaces = {}
        self._load_ontology()
    
    def _load_ontology(self) -> None:
        """
        Load the ontology file into the RDF graph.
        
        Raises:
            FileNotFoundError: If the ontology file doesn't exist
            Exception: If there's an error parsing the ontology
        """
        try:
            if not self.ontology_path.exists():
                raise FileNotFoundError(
                    ErrorMessages.ONTOLOGY_LOAD_ERROR.format(
                        error=f"File not found: {self.ontology_path}"
                    )
                )
            
            logger.info(f"Loading ontology from: {self.ontology_path}")
            self.graph.parse(str(self.ontology_path), format="turtle")
            
            # Extract namespaces from the graph
            self._extract_namespaces()
            
            logger.info(f"Ontology loaded successfully. {len(self.graph)} triples found.")
            
        except Exception as e:
            error_msg = ErrorMessages.ONTOLOGY_LOAD_ERROR.format(error=str(e))
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def _extract_namespaces(self) -> None:
        """Extract namespaces from the loaded ontology."""
        for prefix, namespace in self.graph.namespaces():
            self.namespaces[prefix] = namespace
            logger.debug(f"Found namespace: {prefix} -> {namespace}")
    
    def get_dimension_classes(self) -> List[Dict[str, Any]]:
        """
        Extract dimension classes and their properties from the ontology.
        
        Returns:
            List of dictionaries containing class information with properties
        """
        dimension_classes = []
        
        for class_name in OntologyConfig.DIMENSION_CLASSES:
            class_info = self._get_class_info(class_name)
            if class_info:
                dimension_classes.append(class_info)
                logger.debug(f"Extracted class: {class_name}")
        
        logger.info(f"Extracted {len(dimension_classes)} dimension classes")
        return dimension_classes
    
    def _get_class_info(self, class_name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific class.
        
        Args:
            class_name: Name of the class to extract
            
        Returns:
            Dictionary containing class information or None if not found
        """
        # Find the class URI
        class_uri = self._find_class_uri(class_name)
        if not class_uri:
            logger.warning(f"Class not found: {class_name}")
            return None
        
        class_info = {
            "name": class_name,
            "uri": str(class_uri),
            "properties": {}
        }
        
        # Extract properties
        for prop_name in OntologyConfig.EXTRACTION_PROPERTIES:
            prop_value = self._get_property_value(class_uri, prop_name)
            if prop_value:
                class_info["properties"][prop_name] = prop_value
        
        return class_info
    
    def _find_class_uri(self, class_name: str) -> Optional[URIRef]:
        """
        Find the URI of a class by its name.
        
        Args:
            class_name: Name of the class to find
            
        Returns:
            URI of the class or None if not found
        """
        # Try different namespace combinations
        for prefix, namespace in self.namespaces.items():
            potential_uri = URIRef(f"{namespace}{class_name}")
            if (potential_uri, RDF.type, OWL.Class) in self.graph:
                return potential_uri
        
        # Try with default namespace
        default_namespace = self.namespaces.get("", "")
        if default_namespace:
            potential_uri = URIRef(f"{default_namespace}{class_name}")
            if (potential_uri, RDF.type, OWL.Class) in self.graph:
                return potential_uri
        
        return None
    
    def _get_property_value(self, subject: URIRef, property_name: str) -> Optional[str]:
        """
        Get the value of a property for a given subject.
        
        Args:
            subject: URI of the subject
            property_name: Name of the property
            
        Returns:
            Property value as string or None if not found
        """
        # Try different namespace combinations for the property
        for prefix, namespace in self.namespaces.items():
            potential_prop = URIRef(f"{namespace}{property_name}")
            for obj in self.graph.objects(subject, potential_prop):
                if isinstance(obj, Literal):
                    return str(obj)
        
        # Try with default namespace
        default_namespace = self.namespaces.get("", "")
        if default_namespace:
            potential_prop = URIRef(f"{default_namespace}{property_name}")
            for obj in self.graph.objects(subject, potential_prop):
                if isinstance(obj, Literal):
                    return str(obj)
        
        return None
    
    def get_class_hierarchy(self) -> Dict[str, List[str]]:
        """
        Get the class hierarchy from the ontology.
        
        Returns:
            Dictionary mapping parent classes to their subclasses
        """
        hierarchy = {}
        
        for parent, child in self.graph.subject_objects(RDFS.subClassOf):
            parent_name = self._get_local_name(parent)
            child_name = self._get_local_name(child)
            
            if parent_name and child_name:
                if parent_name not in hierarchy:
                    hierarchy[parent_name] = []
                hierarchy[parent_name].append(child_name)
        
        return hierarchy
    
    def _get_local_name(self, uri: URIRef) -> Optional[str]:
        """
        Extract the local name from a URI.
        
        Args:
            uri: URI to extract name from
            
        Returns:
            Local name or None if extraction fails
        """
        try:
            return uri.split("#")[-1] if "#" in uri else uri.split("/")[-1]
        except:
            return None
    
    def get_ontology_metadata(self) -> Dict[str, Any]:
        """
        Get metadata about the loaded ontology.
        
        Returns:
            Dictionary containing ontology metadata
        """
        metadata = {
            "path": str(self.ontology_path),
            "triple_count": len(self.graph),
            "namespaces": dict(self.namespaces),
            "classes": [],
            "properties": []
        }
        
        # Count classes and properties
        for s, p, o in self.graph:
            if p == RDF.type and o == OWL.Class:
                class_name = self._get_local_name(s)
                if class_name:
                    metadata["classes"].append(class_name)
            elif p == RDF.type and o == OWL.ObjectProperty:
                prop_name = self._get_local_name(s)
                if prop_name:
                    metadata["properties"].append(prop_name)
        
        return metadata
    
    def export_to_jsonld(self, output_path: Path) -> None:
        """
        Export the ontology to JSON-LD format.
        
        Args:
            output_path: Path where to save the JSON-LD file
        """
        try:
            jsonld_data = self.graph.serialize(format="json-ld", indent=2)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(jsonld_data)
            logger.info(f"Ontology exported to JSON-LD: {output_path}")
        except Exception as e:
            error_msg = f"Failed to export ontology to JSON-LD: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def validate_ontology(self) -> List[str]:
        """
        Validate the loaded ontology for common issues.
        
        Returns:
            List of validation warnings/errors
        """
        issues = []
        
        # Check if required dimension classes exist
        for class_name in OntologyConfig.DIMENSION_CLASSES:
            if not self._find_class_uri(class_name):
                issues.append(f"Required dimension class not found: {class_name}")
        
        # Check for missing extraction properties
        for class_name in OntologyConfig.DIMENSION_CLASSES:
            class_uri = self._find_class_uri(class_name)
            if class_uri:
                for prop_name in OntologyConfig.EXTRACTION_PROPERTIES:
                    if not self._get_property_value(class_uri, prop_name):
                        issues.append(f"Missing property '{prop_name}' for class '{class_name}'")
        
        if issues:
            logger.warning(f"Ontology validation found {len(issues)} issues")
        else:
            logger.info("Ontology validation passed")
        
        return issues


def load_ontology(ontology_path: Optional[Path] = None) -> OntologyLoader:
    """
    Convenience function to load an ontology.
    
    Args:
        ontology_path: Path to the ontology file
        
    Returns:
        Loaded OntologyLoader instance
    """
    return OntologyLoader(ontology_path)


if __name__ == "__main__":
    # Example usage and testing
    logging.basicConfig(level=logging.INFO)
    
    try:
        loader = load_ontology()
        
        # Get ontology metadata
        metadata = loader.get_ontology_metadata()
        print(f"Loaded ontology with {metadata['triple_count']} triples")
        print(f"Found {len(metadata['classes'])} classes")
        
        # Get dimension classes
        dimension_classes = loader.get_dimension_classes()
        print(f"Extracted {len(dimension_classes)} dimension classes")
        
        # Validate ontology
        issues = loader.validate_ontology()
        if issues:
            print("Validation issues:")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print("Ontology validation passed")
            
    except Exception as e:
        print(f"Error: {e}")
