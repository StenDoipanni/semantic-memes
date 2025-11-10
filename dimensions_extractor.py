"""
Dimensions Extraction Component.

This module implements the core functionality for extracting structured dimensions
from memes using LLMs and ontological knowledge. It processes images through
different dimension classes and generates structured output.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import re

from ontology_loader import OntologyLoader
from llm_integration import LLMManager
from jsonld_handler import JSONLDHandler
from config import (
    OntologyConfig, 
    PipelineConfig, 
    ErrorMessages, 
    SuccessMessages
)

logger = logging.getLogger(__name__)


class DimensionsExtractor:
    """
    Main component for extracting dimensions from memes.
    
    This class orchestrates the process of analyzing memes using LLMs guided by
    ontological knowledge to extract structured dimension data.
    """
    
    def __init__(
        self, 
        ontology_loader: Optional[OntologyLoader] = None,
        llm_manager: Optional[LLMManager] = None,
        jsonld_handler: Optional[JSONLDHandler] = None
    ):
        """
        Initialize the dimensions extractor.
        
        Args:
            ontology_loader: Ontology loader instance. If None, creates new one.
            llm_manager: LLM manager instance. If None, creates new one.
            jsonld_handler: JSON-LD handler instance. If None, creates new one.
        """
        self.ontology_loader = ontology_loader or OntologyLoader()
        self.llm_manager = llm_manager or LLMManager()
        self.jsonld_handler = jsonld_handler or JSONLDHandler()
        
        # Load dimension classes from ontology
        self.dimension_classes = self.ontology_loader.get_dimension_classes()
        
        logger.info(f"Dimensions extractor initialized with {len(self.dimension_classes)} dimension classes")
    
    def extract_dimensions(
        self, 
        image_path: Path,
        selected_dimensions: Optional[List[str]] = None,
        llm_provider: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract dimensions from a meme image.
        
        Args:
            image_path: Path to the meme image
            selected_dimensions: List of dimension class names to extract. If None, extracts all.
            llm_provider: Specific LLM provider to use ("claude" or "huggingface")
            
        Returns:
            Dictionary containing extracted dimensions and metadata
            
        Raises:
            Exception: If extraction fails
        """
        try:
            # Validate input
            self._validate_image_path(image_path)
            
            # Filter dimension classes if specified
            classes_to_extract = self._filter_dimension_classes(selected_dimensions)
            
            logger.info(f"Extracting dimensions from: {image_path}")
            logger.info(f"Processing {len(classes_to_extract)} dimension classes")
            
            # Extract dimensions for each class
            extracted_dimensions = []
            extraction_metadata = {
                "image_path": str(image_path),
                "image_name": image_path.name,
                "extraction_timestamp": None,
                "llm_provider": None,
                "dimension_classes_processed": [],
                "total_dimensions_found": 0
            }
            
            for class_info in classes_to_extract:
                try:
                    dimensions = self._extract_class_dimensions(
                        image_path, class_info, llm_provider
                    )
                    if dimensions:
                        extracted_dimensions.extend(dimensions)
                        extraction_metadata["dimension_classes_processed"].append(
                            class_info["name"]
                        )
                        logger.debug(f"Extracted {len(dimensions)} dimensions for class: {class_info['name']}")
                    
                except Exception as e:
                    logger.warning(f"Failed to extract dimensions for class {class_info['name']}: {e}")
                    continue
            
            # Update metadata
            extraction_metadata["extraction_timestamp"] = self._get_timestamp()
            extraction_metadata["total_dimensions_found"] = len(extracted_dimensions)
            
            # Create result
            result = {
                "dimensions": extracted_dimensions,
                "metadata": extraction_metadata,
                "success": True
            }
            
            logger.info(SuccessMessages.DIMENSIONS_EXTRACTED.format(count=len(extracted_dimensions)))
            return result
            
        except Exception as e:
            error_msg = ErrorMessages.DIMENSION_EXTRACTION_ERROR.format(error=str(e))
            logger.error(error_msg)
            return {
                "dimensions": [],
                "metadata": {"error": error_msg},
                "success": False
            }
    
    def _validate_image_path(self, image_path: Path) -> None:
        """
        Validate the input image path.
        
        Args:
            image_path: Path to validate
            
        Raises:
            ValueError: If the path is invalid
        """
        if not image_path.exists():
            raise ValueError(ErrorMessages.IMAGE_NOT_FOUND.format(path=image_path))
        
        if image_path.suffix.lower() not in PipelineConfig.SUPPORTED_IMAGE_FORMATS:
            raise ValueError(
                ErrorMessages.INVALID_IMAGE_FORMAT.format(
                    formats=PipelineConfig.SUPPORTED_IMAGE_FORMATS
                )
            )
    
    def _filter_dimension_classes(self, selected_dimensions: Optional[List[str]]) -> List[Dict[str, Any]]:
        """
        Filter dimension classes based on selection.
        
        Args:
            selected_dimensions: List of dimension class names to include
            
        Returns:
            Filtered list of dimension class information
        """
        if selected_dimensions is None:
            return self.dimension_classes
        
        filtered_classes = []
        for class_info in self.dimension_classes:
            if class_info["name"] in selected_dimensions:
                filtered_classes.append(class_info)
        
        return filtered_classes
    
    def _extract_class_dimensions(
        self, 
        image_path: Path, 
        class_info: Dict[str, Any],
        llm_provider: Optional[str]
    ) -> List[Dict[str, Any]]:
        """
        Extract dimensions for a specific class.
        
        Args:
            image_path: Path to the image
            class_info: Information about the dimension class
            llm_provider: LLM provider to use
            
        Returns:
            List of extracted dimension instances
        """
        # Get extraction prompt from class properties
        extraction_prompt = class_info["properties"].get("promptExtractionText")
        if not extraction_prompt:
            logger.warning(f"No extraction prompt found for class: {class_info['name']}")
            return []
        
        # Create the full prompt
        full_prompt = self._create_extraction_prompt(extraction_prompt, class_info)
        
        # Generate response using LLM
        try:
            response = self.llm_manager.generate_response(
                full_prompt, 
                image_path, 
                provider=llm_provider
            )
            
            # Parse the response
            dimensions = self._parse_extraction_response(response, class_info)
            
            return dimensions
            
        except Exception as e:
            logger.error(f"LLM extraction failed for class {class_info['name']}: {e}")
            return []
    
    def _create_extraction_prompt(
        self, 
        base_prompt: str, 
        class_info: Dict[str, Any]
    ) -> str:
        """
        Create the full extraction prompt for a dimension class.
        
        Args:
            base_prompt: Base prompt from ontology
            class_info: Information about the dimension class
            
        Returns:
            Complete extraction prompt
        """
        # Add class context
        class_name = class_info["name"]
        class_label = class_info["properties"].get("rdfs:label", class_name)
        class_comment = class_info["properties"].get("rdfs:comment", "")
        
        # Create the full prompt
        full_prompt = f"""You are analyzing a meme image to extract {class_label} dimensions.

Class: {class_name}
Description: {class_comment}

{base_prompt}

Please analyze the image and provide your response in the exact JSON format specified in the prompt above. Be thorough and accurate in your analysis."""

        return full_prompt
    
    def _parse_extraction_response(
        self, 
        response: str, 
        class_info: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Parse the LLM response to extract dimension data.
        
        Args:
            response: Raw LLM response
            class_info: Information about the dimension class
            
        Returns:
            List of parsed dimension instances
        """
        dimensions = []
        
        try:
            # Try to extract JSON from the response
            json_data = self._extract_json_from_response(response)
            
            if isinstance(json_data, list):
                # Multiple dimensions
                for item in json_data:
                    dimension = self._create_dimension_instance(item, class_info)
                    if dimension:
                        dimensions.append(dimension)
            elif isinstance(json_data, dict):
                # Single dimension
                dimension = self._create_dimension_instance(json_data, class_info)
                if dimension:
                    dimensions.append(dimension)
            
        except Exception as e:
            logger.warning(f"Failed to parse response for class {class_info['name']}: {e}")
            # Try to extract dimensions using regex as fallback
            dimensions = self._extract_dimensions_with_regex(response, class_info)
        
        return dimensions
    
    def _extract_json_from_response(self, response: str) -> Any:
        """
        Extract JSON data from LLM response.
        
        Args:
            response: Raw LLM response
            
        Returns:
            Parsed JSON data
        """
        # Look for JSON blocks in the response
        json_patterns = [
            r'```json\s*(.*?)\s*```',
            r'```\s*(.*?)\s*```',
            r'\{.*\}',
            r'\[.*\]'
        ]
        
        for pattern in json_patterns:
            matches = re.findall(pattern, response, re.DOTALL)
            for match in matches:
                try:
                    return json.loads(match.strip())
                except json.JSONDecodeError:
                    continue
        
        # If no JSON found, try parsing the entire response
        try:
            return json.loads(response.strip())
        except json.JSONDecodeError:
            raise ValueError("No valid JSON found in response")
    
    def _create_dimension_instance(
        self, 
        data: Dict[str, Any], 
        class_info: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Create a dimension instance from parsed data.
        
        Args:
            data: Parsed dimension data
            class_info: Information about the dimension class
            
        Returns:
            Formatted dimension instance or None if invalid
        """
        try:
            # Validate required fields
            required_fields = ["instance_name", "label", "description"]
            if not all(field in data for field in required_fields):
                logger.warning(f"Missing required fields in dimension data: {data}")
                return None
            
            # Create the dimension instance
            dimension = {
                "class_name": class_info["name"],
                "class_uri": class_info["uri"],
                "instance_name": data["instance_name"],
                "label": data["label"],
                "description": data["description"],
                "extraction_method": "llm_analysis",
                "confidence": data.get("confidence", 0.8)
            }
            
            # Add additional fields if present
            if "metadata" in data:
                dimension["metadata"] = data["metadata"]
            
            return dimension
            
        except Exception as e:
            logger.error(f"Error creating dimension instance: {e}")
            return None
    
    def _extract_dimensions_with_regex(
        self, 
        response: str, 
        class_info: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Extract dimensions using regex patterns as fallback.
        
        Args:
            response: Raw LLM response
            class_info: Information about the dimension class
            
        Returns:
            List of extracted dimension instances
        """
        dimensions = []
        
        # Simple regex patterns to extract dimension information
        patterns = {
            "instance_name": r'instance_name["\']?\s*:\s*["\']([^"\']+)["\']',
            "label": r'label["\']?\s*:\s*["\']([^"\']+)["\']',
            "description": r'description["\']?\s*:\s*["\']([^"\']+)["\']'
        }
        
        # Try to extract at least one dimension
        instance_names = re.findall(patterns["instance_name"], response, re.IGNORECASE)
        labels = re.findall(patterns["label"], response, re.IGNORECASE)
        descriptions = re.findall(patterns["description"], response, re.IGNORECASE)
        
        # Create dimensions from extracted data
        max_items = max(len(instance_names), len(labels), len(descriptions))
        
        for i in range(max_items):
            try:
                dimension = {
                    "class_name": class_info["name"],
                    "class_uri": class_info["uri"],
                    "instance_name": instance_names[i] if i < len(instance_names) else f"dimension_{i+1}",
                    "label": labels[i] if i < len(labels) else f"the {class_info['name'].lower()}",
                    "description": descriptions[i] if i < len(descriptions) else "Extracted from image analysis",
                    "extraction_method": "regex_fallback",
                    "confidence": 0.5
                }
                dimensions.append(dimension)
            except Exception as e:
                logger.warning(f"Error creating fallback dimension {i}: {e}")
                continue
        
        return dimensions
    
    def _get_timestamp(self) -> str:
        """Get current timestamp as ISO string."""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def save_extraction_results(
        self, 
        results: Dict[str, Any], 
        output_dir: Path,
        image_path: Path
    ) -> Dict[str, Path]:
        """
        Save extraction results to files.
        
        Args:
            results: Extraction results dictionary
            output_dir: Directory to save files
            image_path: Path to the analyzed image
            
        Returns:
            Dictionary mapping file types to saved file paths
        """
        saved_files = {}
        
        try:
            # Create output directory
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate base filename
            base_name = image_path.stem
            
            # Save standalone JSON-LD
            if results["success"] and results["dimensions"]:
                jsonld_doc = self.jsonld_handler.create_dimensions_jsonld(
                    results["dimensions"], 
                    image_path, 
                    results["metadata"]
                )
                
                jsonld_path = output_dir / f"{base_name}_dimensions.jsonld"
                self.jsonld_handler.save_jsonld(jsonld_doc, jsonld_path)
                saved_files["dimensions_jsonld"] = jsonld_path
                
                # Save raw JSON for debugging
                raw_json_path = output_dir / f"{base_name}_dimensions_raw.json"
                with open(raw_json_path, 'w', encoding='utf-8') as f:
                    json.dump(results, f, indent=2, ensure_ascii=False)
                saved_files["raw_json"] = raw_json_path
            
            # Save text summary
            text_path = output_dir / f"{base_name}_dimensions.txt"
            self._save_text_summary(results, text_path)
            saved_files["text_summary"] = text_path
            
            logger.info(f"Extraction results saved to: {output_dir}")
            return saved_files
            
        except Exception as e:
            logger.error(f"Failed to save extraction results: {e}")
            return {}
    
    def _save_text_summary(self, results: Dict[str, Any], output_path: Path) -> None:
        """
        Save a text summary of extraction results.
        
        Args:
            results: Extraction results
            output_path: Path to save the summary
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"Dimension Extraction Results\n")
            f.write(f"============================\n\n")
            
            if results["success"]:
                f.write(f"Image: {results['metadata']['image_name']}\n")
                f.write(f"Extraction Time: {results['metadata']['extraction_timestamp']}\n")
                f.write(f"LLM Provider: {results['metadata'].get('llm_provider', 'Unknown')}\n")
                f.write(f"Total Dimensions Found: {results['metadata']['total_dimensions_found']}\n\n")
                
                f.write("Extracted Dimensions:\n")
                f.write("-------------------\n")
                
                for i, dim in enumerate(results["dimensions"], 1):
                    f.write(f"{i}. {dim['class_name']}: {dim['label']}\n")
                    f.write(f"   Description: {dim['description']}\n")
                    f.write(f"   Confidence: {dim.get('confidence', 'N/A')}\n\n")
            else:
                f.write(f"Extraction failed: {results['metadata'].get('error', 'Unknown error')}\n")


# Convenience functions
def extract_dimensions_from_image(
    image_path: Path,
    selected_dimensions: Optional[List[str]] = None,
    llm_provider: Optional[str] = None,
    output_dir: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Extract dimensions from a meme image.
    
    Args:
        image_path: Path to the meme image
        selected_dimensions: List of dimension classes to extract
        llm_provider: LLM provider to use
        output_dir: Directory to save results
        
    Returns:
        Extraction results dictionary
    """
    extractor = DimensionsExtractor()
    results = extractor.extract_dimensions(image_path, selected_dimensions, llm_provider)
    
    if output_dir and results["success"]:
        saved_files = extractor.save_extraction_results(results, output_dir, image_path)
        results["saved_files"] = saved_files
    
    return results


if __name__ == "__main__":
    # Example usage and testing
    import logging
    logging.basicConfig(level=logging.INFO)
    
    try:
        # Test with the provided meme image
        image_path = Path("/Users/stefanodegiorgis/Downloads/dev_set_task3_labeled/9_image_batch_2.png")
        
        if image_path.exists():
            # Extract dimensions
            results = extract_dimensions_from_image(
                image_path,
                selected_dimensions=["OverallIntent", "VisualMaterial", "TextualMaterial"],
                output_dir=Path("output/test_extraction")
            )
            
            print(f"Extraction successful: {results['success']}")
            print(f"Dimensions found: {len(results['dimensions'])}")
            
            if results["success"]:
                for dim in results["dimensions"]:
                    print(f"- {dim['class_name']}: {dim['label']}")
        else:
            print(f"Test image not found: {image_path}")
            
    except Exception as e:
        print(f"Error: {e}")
