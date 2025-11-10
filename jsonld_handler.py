"""
JSON-LD Handler Module.

This module handles the creation, formatting, and integration of JSON-LD output files.
It provides functionality to create standalone JSON-LD files and unified files that
combine extracted dimensions with the original ontology.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import uuid

from config import ValidationConfig, ErrorMessages

logger = logging.getLogger(__name__)


class JSONLDHandler:
    """
    Handles JSON-LD creation and formatting for meme analysis output.
    
    This class provides methods to create properly formatted JSON-LD files
    with extracted dimensions and Q&A data, following semantic web standards.
    """
    
    def __init__(self, base_context: Optional[Dict[str, str]] = None):
        """
        Initialize the JSON-LD handler.
        
        Args:
            base_context: Base JSON-LD context to use. If None, uses default from config.
        """
        self.base_context = base_context or ValidationConfig.JSONLD_CONTEXT.copy()
        self.namespace_base = "http://example.org/multimodal-taxonomy#"
    
    def create_dimensions_jsonld(
        self, 
        dimensions_data: List[Dict[str, Any]], 
        image_path: Path,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a JSON-LD document for extracted dimensions.
        
        Args:
            dimensions_data: List of extracted dimension data
            image_path: Path to the analyzed image
            metadata: Optional metadata about the analysis
            
        Returns:
            JSON-LD document as dictionary
        """
        # Generate unique IDs for the analysis
        analysis_id = f"analysis_{uuid.uuid4().hex[:8]}"
        image_id = f"image_{uuid.uuid4().hex[:8]}"
        
        # Create the main document structure
        jsonld_doc = {
            "@context": self.base_context.copy(),
            "@id": f"{self.namespace_base}{analysis_id}",
            "@type": "AnalysisDocument",
            "title": f"{image_path.name} - Dimension Analysis",
            "created": datetime.now().isoformat(),
            "analyzedImage": {
                "@id": f"{self.namespace_base}{image_id}",
                "@type": "Image",
                "filename": image_path.name,
                "path": str(image_path)
            }
        }
        
        # Add metadata if provided
        if metadata:
            jsonld_doc["metadata"] = metadata
        
        # Process dimensions data
        dimensions = []
        for dim_data in dimensions_data:
            dimension = self._create_dimension_jsonld(dim_data, analysis_id)
            if dimension:
                dimensions.append(dimension)
        
        jsonld_doc["dimensions"] = dimensions
        
        logger.info(f"Created JSON-LD document with {len(dimensions)} dimensions")
        return jsonld_doc
    
    def _create_dimension_jsonld(
        self, 
        dim_data: Dict[str, Any], 
        analysis_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Create JSON-LD representation for a single dimension.
        
        Args:
            dim_data: Dimension data dictionary
            analysis_id: ID of the parent analysis
            
        Returns:
            JSON-LD dimension object or None if invalid
        """
        try:
            # Validate required fields
            if not self._validate_dimension_data(dim_data):
                logger.warning(f"Invalid dimension data: {dim_data}")
                return None
            
            # Generate unique ID for this dimension instance
            dim_id = f"dimension_{uuid.uuid4().hex[:8]}"
            
            # Create the dimension object
            dimension = {
                "@id": f"{self.namespace_base}{dim_id}",
                "@type": dim_data.get("class_name", "Dimension"),
                "instance_name": dim_data.get("instance_name"),
                "label": dim_data.get("label"),
                "description": dim_data.get("description"),
                "belongsToAnalysis": {
                    "@id": f"{self.namespace_base}{analysis_id}"
                }
            }
            
            # Add additional properties if present
            if "confidence" in dim_data:
                dimension["confidence"] = dim_data["confidence"]
            
            if "extraction_method" in dim_data:
                dimension["extractionMethod"] = dim_data["extraction_method"]
            
            return dimension
            
        except Exception as e:
            logger.error(f"Error creating dimension JSON-LD: {e}")
            return None
    
    def create_qa_jsonld(
        self, 
        qa_data: List[Dict[str, Any]], 
        image_path: Path,
        dimensions_data: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a JSON-LD document for Q&A data.
        
        Args:
            qa_data: List of Q&A data
            image_path: Path to the analyzed image
            dimensions_data: Optional dimensions data for context
            metadata: Optional metadata about the analysis
            
        Returns:
            JSON-LD document as dictionary
        """
        # Generate unique IDs
        qa_id = f"qa_{uuid.uuid4().hex[:8]}"
        image_id = f"image_{uuid.uuid4().hex[:8]}"
        
        # Create the main document structure
        jsonld_doc = {
            "@context": self.base_context.copy(),
            "@id": f"{self.namespace_base}{qa_id}",
            "@type": "QADocument",
            "title": f"{image_path.name} - Questions and Answers",
            "created": datetime.now().isoformat(),
            "analyzedImage": {
                "@id": f"{self.namespace_base}{image_id}",
                "@type": "Image",
                "filename": image_path.name,
                "path": str(image_path)
            }
        }
        
        # Add metadata if provided
        if metadata:
            jsonld_doc["metadata"] = metadata
        
        # Process Q&A data
        qa_pairs = []
        for qa_item in qa_data:
            qa_pair = self._create_qa_jsonld(qa_item, qa_id)
            if qa_pair:
                qa_pairs.append(qa_pair)
        
        jsonld_doc["qaPairs"] = qa_pairs
        
        # Add dimensions context if provided
        if dimensions_data:
            jsonld_doc["contextDimensions"] = [
                self._create_dimension_jsonld(dim, qa_id) 
                for dim in dimensions_data
            ]
        
        logger.info(f"Created JSON-LD document with {len(qa_pairs)} Q&A pairs")
        return jsonld_doc
    
    def _create_qa_jsonld(
        self, 
        qa_data: Dict[str, Any], 
        parent_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Create JSON-LD representation for a single Q&A pair.
        
        Args:
            qa_data: Q&A data dictionary
            parent_id: ID of the parent document
            
        Returns:
            JSON-LD Q&A object or None if invalid
        """
        try:
            # Validate required fields
            if not self._validate_qa_data(qa_data):
                logger.warning(f"Invalid Q&A data: {qa_data}")
                return None
            
            # Generate unique ID for this Q&A pair
            qa_pair_id = f"qa_pair_{uuid.uuid4().hex[:8]}"
            
            # Create the Q&A object
            qa_pair = {
                "@id": f"{self.namespace_base}{qa_pair_id}",
                "@type": "QAPair",
                "question": qa_data.get("question"),
                "answer": qa_data.get("answer"),
                "belongsToDocument": {
                    "@id": f"{self.namespace_base}{parent_id}"
                }
            }
            
            # Add additional properties if present
            if "question_type" in qa_data:
                qa_pair["questionType"] = qa_data["question_type"]
            
            if "confidence" in qa_data:
                qa_pair["confidence"] = qa_data["confidence"]
            
            if "related_dimensions" in qa_data:
                qa_pair["relatedDimensions"] = qa_data["related_dimensions"]
            
            return qa_pair
            
        except Exception as e:
            logger.error(f"Error creating Q&A JSON-LD: {e}")
            return None
    
    def create_unified_jsonld(
        self, 
        dimensions_data: List[Dict[str, Any]], 
        qa_data: List[Dict[str, Any]], 
        image_path: Path,
        original_ontology: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a unified JSON-LD document combining dimensions, Q&A, and ontology.
        
        Args:
            dimensions_data: List of extracted dimension data
            qa_data: List of Q&A data
            image_path: Path to the analyzed image
            original_ontology: Optional original ontology data
            metadata: Optional metadata about the analysis
            
        Returns:
            Unified JSON-LD document as dictionary
        """
        # Generate unique ID for the unified document
        unified_id = f"unified_{uuid.uuid4().hex[:8]}"
        
        # Create the main document structure
        jsonld_doc = {
            "@context": self.base_context.copy(),
            "@id": f"{self.namespace_base}{unified_id}",
            "@type": "UnifiedAnalysisDocument",
            "title": f"{image_path.name} - Complete Analysis",
            "created": datetime.now().isoformat(),
            "analyzedImage": {
                "@id": f"{self.namespace_base}image_{uuid.uuid4().hex[:8]}",
                "@type": "Image",
                "filename": image_path.name,
                "path": str(image_path)
            }
        }
        
        # Add metadata if provided
        if metadata:
            jsonld_doc["metadata"] = metadata
        
        # Add original ontology if provided
        if original_ontology:
            jsonld_doc["ontology"] = original_ontology
        
        # Add dimensions
        dimensions = []
        for dim_data in dimensions_data:
            dimension = self._create_dimension_jsonld(dim_data, unified_id)
            if dimension:
                dimensions.append(dimension)
        jsonld_doc["dimensions"] = dimensions
        
        # Add Q&A pairs
        qa_pairs = []
        for qa_item in qa_data:
            qa_pair = self._create_qa_jsonld(qa_item, unified_id)
            if qa_pair:
                qa_pairs.append(qa_pair)
        jsonld_doc["qaPairs"] = qa_pairs
        
        logger.info(f"Created unified JSON-LD document with {len(dimensions)} dimensions and {len(qa_pairs)} Q&A pairs")
        return jsonld_doc
    
    def save_jsonld(
        self, 
        jsonld_doc: Dict[str, Any], 
        output_path: Path,
        pretty_print: bool = True
    ) -> None:
        """
        Save a JSON-LD document to file.
        
        Args:
            jsonld_doc: JSON-LD document to save
            output_path: Path where to save the file
            pretty_print: Whether to format the JSON with indentation
            
        Raises:
            Exception: If saving fails
        """
        try:
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Format JSON
            indent = 2 if pretty_print else None
            json_str = json.dumps(jsonld_doc, indent=indent, ensure_ascii=False)
            
            # Write to file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(json_str)
            
            logger.info(f"JSON-LD document saved to: {output_path}")
            
        except Exception as e:
            error_msg = ErrorMessages.JSONLD_SERIALIZATION_ERROR.format(error=str(e))
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def load_jsonld(self, input_path: Path) -> Dict[str, Any]:
        """
        Load a JSON-LD document from file.
        
        Args:
            input_path: Path to the JSON-LD file
            
        Returns:
            Loaded JSON-LD document
            
        Raises:
            Exception: If loading fails
        """
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                jsonld_doc = json.load(f)
            
            logger.info(f"JSON-LD document loaded from: {input_path}")
            return jsonld_doc
            
        except Exception as e:
            error_msg = f"Failed to load JSON-LD document: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def validate_jsonld(self, jsonld_doc: Dict[str, Any]) -> List[str]:
        """
        Validate a JSON-LD document for common issues.
        
        Args:
            jsonld_doc: JSON-LD document to validate
            
        Returns:
            List of validation issues (empty if valid)
        """
        issues = []
        
        # Check for required top-level fields
        required_fields = ["@context", "@id", "@type"]
        for field in required_fields:
            if field not in jsonld_doc:
                issues.append(f"Missing required field: {field}")
        
        # Check context format
        if "@context" in jsonld_doc:
            context = jsonld_doc["@context"]
            if not isinstance(context, dict):
                issues.append("Context must be a dictionary")
        
        # Check for valid types
        if "@type" in jsonld_doc:
            valid_types = ["AnalysisDocument", "QADocument", "UnifiedAnalysisDocument"]
            if jsonld_doc["@type"] not in valid_types:
                issues.append(f"Invalid document type: {jsonld_doc['@type']}")
        
        # Validate dimensions if present
        if "dimensions" in jsonld_doc:
            for i, dim in enumerate(jsonld_doc["dimensions"]):
                if not self._validate_dimension_data(dim):
                    issues.append(f"Invalid dimension at index {i}")
        
        # Validate Q&A pairs if present
        if "qaPairs" in jsonld_doc:
            for i, qa in enumerate(jsonld_doc["qaPairs"]):
                if not self._validate_qa_data(qa):
                    issues.append(f"Invalid Q&A pair at index {i}")
        
        if issues:
            logger.warning(f"JSON-LD validation found {len(issues)} issues")
        else:
            logger.info("JSON-LD validation passed")
        
        return issues
    
    def _validate_dimension_data(self, dim_data: Dict[str, Any]) -> bool:
        """Validate dimension data structure."""
        required_fields = ValidationConfig.REQUIRED_DIMENSION_FIELDS
        return all(field in dim_data for field in required_fields)
    
    def _validate_qa_data(self, qa_data: Dict[str, Any]) -> bool:
        """Validate Q&A data structure."""
        required_fields = ValidationConfig.REQUIRED_QA_FIELDS
        return all(field in qa_data for field in required_fields)
    
    def merge_jsonld_documents(
        self, 
        documents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Merge multiple JSON-LD documents into one.
        
        Args:
            documents: List of JSON-LD documents to merge
            
        Returns:
            Merged JSON-LD document
        """
        if not documents:
            raise ValueError("No documents to merge")
        
        # Use the first document as base
        merged = documents[0].copy()
        
        # Merge additional documents
        for doc in documents[1:]:
            # Merge dimensions
            if "dimensions" in doc:
                if "dimensions" not in merged:
                    merged["dimensions"] = []
                merged["dimensions"].extend(doc["dimensions"])
            
            # Merge Q&A pairs
            if "qaPairs" in doc:
                if "qaPairs" not in merged:
                    merged["qaPairs"] = []
                merged["qaPairs"].extend(doc["qaPairs"])
            
            # Merge metadata
            if "metadata" in doc:
                if "metadata" not in merged:
                    merged["metadata"] = {}
                merged["metadata"].update(doc["metadata"])
        
        # Update document type and title
        merged["@type"] = "MergedAnalysisDocument"
        merged["title"] = "Merged Analysis Document"
        merged["created"] = datetime.now().isoformat()
        
        logger.info(f"Merged {len(documents)} JSON-LD documents")
        return merged


# Convenience functions
def create_dimensions_jsonld(
    dimensions_data: List[Dict[str, Any]], 
    image_path: Path,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Create a JSON-LD document for dimensions data."""
    handler = JSONLDHandler()
    return handler.create_dimensions_jsonld(dimensions_data, image_path, metadata)


def create_qa_jsonld(
    qa_data: List[Dict[str, Any]], 
    image_path: Path,
    dimensions_data: Optional[List[Dict[str, Any]]] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Create a JSON-LD document for Q&A data."""
    handler = JSONLDHandler()
    return handler.create_qa_jsonld(qa_data, image_path, dimensions_data, metadata)


def save_jsonld(
    jsonld_doc: Dict[str, Any], 
    output_path: Path,
    pretty_print: bool = True
) -> None:
    """Save a JSON-LD document to file."""
    handler = JSONLDHandler()
    handler.save_jsonld(jsonld_doc, output_path, pretty_print)


if __name__ == "__main__":
    # Example usage and testing
    logging.basicConfig(level=logging.INFO)
    
    try:
        handler = JSONLDHandler()
        
        # Test data
        test_dimensions = [
            {
                "class_name": "VisualMaterial",
                "instance_name": "smiling_girl",
                "label": "the smiling girl",
                "description": "A young girl with a mischievous smile in the foreground"
            }
        ]
        
        test_qa = [
            {
                "question": "What visual elements are present in this meme?",
                "answer": "The meme shows a smiling girl in the foreground with a burning house in the background.",
                "question_type": "descriptive"
            }
        ]
        
        # Create JSON-LD documents
        image_path = Path("test_image.png")
        
        dimensions_doc = handler.create_dimensions_jsonld(test_dimensions, image_path)
        qa_doc = handler.create_qa_jsonld(test_qa, image_path, test_dimensions)
        unified_doc = handler.create_unified_jsonld(test_dimensions, test_qa, image_path)
        
        # Validate documents
        dim_issues = handler.validate_jsonld(dimensions_doc)
        qa_issues = handler.validate_jsonld(qa_doc)
        unified_issues = handler.validate_jsonld(unified_doc)
        
        print(f"Dimensions document validation: {len(dim_issues)} issues")
        print(f"Q&A document validation: {len(qa_issues)} issues")
        print(f"Unified document validation: {len(unified_issues)} issues")
        
        if not (dim_issues or qa_issues or unified_issues):
            print("All JSON-LD documents are valid!")
        
    except Exception as e:
        print(f"Error: {e}")
