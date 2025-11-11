"""
Specialized Dimension Extraction Module.

This module implements dimension extraction using the specific JSON-LD prompt files
from the prompts directory and integrates with the ontology to generate both
standalone JSON-LD files and enhanced TTL files.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
import os
from datetime import datetime

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


class DimensionExtractionModule:
    """
    Specialized module for dimension extraction using JSON-LD prompt files.
    
    This module loads prompts from JSON-LD files, uses them with Claude API
    to extract dimensions, and generates both standalone JSON-LD and enhanced TTL files.
    """
    
    def __init__(
        self, 
        ontology_path: Optional[Path] = None,
        prompts_dir: Optional[Path] = None,
        llm_provider: str = "claude"
    ):
        """
        Initialize the dimension extraction module.
        
        Args:
            ontology_path: Path to the ontology file
            prompts_dir: Directory containing JSON-LD prompt files
            llm_provider: LLM provider to use ("claude" or "huggingface")
        """
        self.ontology_path = ontology_path or OntologyConfig.ONTOLOGY_PATH
        self.prompts_dir = prompts_dir or OntologyConfig.PROMPTS_DIR
        self.llm_provider = llm_provider
        
        # Initialize components
        self.ontology_loader = OntologyLoader(self.ontology_path)
        self.llm_manager = LLMManager()
        self.jsonld_handler = JSONLDHandler()
        
        # Load prompt files
        self.prompt_files = self._load_prompt_files()
        
        logger.info(f"Dimension extraction module initialized with {len(self.prompt_files)} prompt files")
    
    def _get_ordered_dimensions(self, selected_dimensions: Optional[List[str]] = None) -> List[str]:
        """
        Get dimensions in the required extraction order.
        
        Core order: TextualMaterial → VisualMaterial → BackgroundKnowledge
        Then any remaining dimensions in their original order.
        
        Args:
            selected_dimensions: List of selected dimensions, or None for all
            
        Returns:
            List of dimensions in the correct extraction order
        """
        # Define the core extraction order
        core_order = ["TextualMaterial", "VisualMaterial", "BackgroundKnowledge"]
        
        # Get all available dimensions
        all_dimensions = list(self.prompt_files.keys())
        
        # If specific dimensions are selected, use those
        if selected_dimensions:
            # Ensure core dimensions come first in order
            ordered_dimensions = []
            
            # Add core dimensions in order if they're selected
            for core_dim in core_order:
                if core_dim in selected_dimensions:
                    ordered_dimensions.append(core_dim)
            
            # Add remaining selected dimensions
            for dim in selected_dimensions:
                if dim not in ordered_dimensions:
                    ordered_dimensions.append(dim)
            
            return ordered_dimensions
        
        # If no specific dimensions, use core order first, then others
        else:
            # Start with core order
            ordered_dimensions = []
            for core_dim in core_order:
                if core_dim in all_dimensions:
                    ordered_dimensions.append(core_dim)
            
            # Add remaining dimensions
            for dim in all_dimensions:
                if dim not in ordered_dimensions:
                    ordered_dimensions.append(dim)
            
            return ordered_dimensions
    
    def _load_prompt_files(self) -> Dict[str, Dict[str, Any]]:
        """
        Load all JSON-LD prompt files from the prompts directory.
        
        Returns:
            Dictionary mapping dimension names to prompt data
        """
        prompt_files = {}
        
        if not self.prompts_dir.exists():
            logger.warning(f"Prompts directory not found: {self.prompts_dir}")
            return prompt_files
        
        for prompt_file in self.prompts_dir.glob("*.jsonld"):
            try:
                with open(prompt_file, 'r', encoding='utf-8') as f:
                    prompt_data = json.load(f)
                
                # Extract dimension name from @id
                dimension_name = prompt_data.get("@id", prompt_file.stem)
                prompt_files[dimension_name] = prompt_data
                
                logger.debug(f"Loaded prompt file: {prompt_file.name} -> {dimension_name}")
                
            except Exception as e:
                logger.error(f"Failed to load prompt file {prompt_file}: {e}")
                continue
        
        return prompt_files
    
    def extract_dimensions_from_image(
        self, 
        image_path: Path,
        selected_dimensions: Optional[List[str]] = None,
        output_dir: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Extract dimensions from an image using the loaded prompt files.
        
        Args:
            image_path: Path to the meme image
            selected_dimensions: List of dimension names to extract
            output_dir: Directory to save output files
            
        Returns:
            Dictionary containing extraction results and metadata
        """
        try:
            # Validate input
            self._validate_image_path(image_path)
            
            # Determine which dimensions to extract with specific order
            dimensions_to_extract = self._get_ordered_dimensions(selected_dimensions)
            
            logger.info(f"Extracting dimensions from: {image_path}")
            logger.info(f"Processing {len(dimensions_to_extract)} dimensions in order: {dimensions_to_extract}")
            
            # Extract dimensions
            extracted_dimensions = []
            extraction_metadata = {
                "image_path": str(image_path),
                "image_name": image_path.name,
                "extraction_timestamp": datetime.now().isoformat(),
                "llm_provider": self.llm_provider,
                "dimensions_processed": [],
                "total_dimensions_found": 0
            }
            
            # Store VisualMaterial and TextualMaterial entities for Scene and BackgroundKnowledge
            # Store BackgroundKnowledge entities for AnalogicalMapping
            # Store AnalogicalMapping entities for ToxicityAssessment
            visual_material_entities = []
            textual_material_entities = []
            background_knowledge_entities = []
            metaphorical_mapping_entities = []
            
            for dimension_name in dimensions_to_extract:
                if dimension_name not in self.prompt_files:
                    logger.warning(f"Prompt file not found for dimension: {dimension_name}")
                    continue
                
                try:
                    # For Scene, pass VisualMaterial entities
                    if dimension_name == "Scene" and visual_material_entities:
                        dimensions = self._extract_single_dimension(
                            image_path, 
                            dimension_name, 
                            self.prompt_files[dimension_name],
                            visual_material_entities=visual_material_entities
                        )
                    # For BackgroundKnowledge, pass both VisualMaterial and TextualMaterial entities
                    elif dimension_name == "BackgroundKnowledge":
                        if visual_material_entities or textual_material_entities:
                            logger.info(f"Extracting BackgroundKnowledge with {len(visual_material_entities)} VisualMaterial and {len(textual_material_entities)} TextualMaterial entities")
                            dimensions = self._extract_single_dimension(
                                image_path, 
                                dimension_name, 
                                self.prompt_files[dimension_name],
                                visual_material_entities=visual_material_entities,
                                textual_material_entities=textual_material_entities
                            )
                        else:
                            logger.warning(f"BackgroundKnowledge extraction skipped: No VisualMaterial or TextualMaterial entities available yet")
                            dimensions = []
                    # For EmotionExpression, pass both VisualMaterial and TextualMaterial entities
                    elif dimension_name == "EmotionExpression":
                        if visual_material_entities or textual_material_entities:
                            logger.info(f"Extracting EmotionExpression with {len(visual_material_entities)} VisualMaterial and {len(textual_material_entities)} TextualMaterial entities")
                            dimensions = self._extract_single_dimension(
                                image_path, 
                                dimension_name, 
                                self.prompt_files[dimension_name],
                                visual_material_entities=visual_material_entities,
                                textual_material_entities=textual_material_entities
                            )
                        else:
                            logger.warning(f"EmotionExpression extraction skipped: No VisualMaterial or TextualMaterial entities available yet")
                            dimensions = []
                    # For AnalogicalMapping, pass VisualMaterial, TextualMaterial, and BackgroundKnowledge entities
                    elif dimension_name == "AnalogicalMapping":
                        if visual_material_entities or textual_material_entities or background_knowledge_entities:
                            logger.info(f"Extracting AnalogicalMapping with {len(visual_material_entities)} VisualMaterial, {len(textual_material_entities)} TextualMaterial, and {len(background_knowledge_entities)} BackgroundKnowledge entities")
                            dimensions = self._extract_single_dimension(
                                image_path, 
                                dimension_name, 
                                self.prompt_files[dimension_name],
                                visual_material_entities=visual_material_entities,
                                textual_material_entities=textual_material_entities,
                                background_knowledge_entities=background_knowledge_entities
                            )
                        else:
                            logger.warning(f"AnalogicalMapping extraction skipped: No VisualMaterial, TextualMaterial, or BackgroundKnowledge entities available yet")
                            dimensions = []
                    # For ToxicityAssessment, pass VisualMaterial, TextualMaterial, BackgroundKnowledge, and AnalogicalMapping entities
                    elif dimension_name == "ToxicityAssessment":
                        if visual_material_entities or textual_material_entities or background_knowledge_entities or metaphorical_mapping_entities:
                            logger.info(f"Extracting ToxicityAssessment with {len(visual_material_entities)} VisualMaterial, {len(textual_material_entities)} TextualMaterial, {len(background_knowledge_entities)} BackgroundKnowledge, and {len(metaphorical_mapping_entities)} AnalogicalMapping entities")
                            dimensions = self._extract_single_dimension(
                                image_path, 
                                dimension_name, 
                                self.prompt_files[dimension_name],
                                visual_material_entities=visual_material_entities,
                                textual_material_entities=textual_material_entities,
                                background_knowledge_entities=background_knowledge_entities,
                                metaphorical_mapping_entities=metaphorical_mapping_entities
                            )
                        else:
                            logger.warning(f"ToxicityAssessment extraction skipped: No VisualMaterial, TextualMaterial, BackgroundKnowledge, or AnalogicalMapping entities available yet")
                            dimensions = []
                    else:
                        dimensions = self._extract_single_dimension(
                            image_path, 
                            dimension_name, 
                            self.prompt_files[dimension_name]
                        )
                    
                    # Handle results (even if empty)
                    if dimensions is not None:
                        # CRITICAL: Normalize all dimension instances BEFORE storing/passing to other phases
                        # This ensures URIs are clean (only underscores, no parentheses or other special chars)
                        if dimensions:
                            for dim in dimensions:
                                if isinstance(dim, dict):
                                    # Normalize the main instance_name
                                    if "instance_name" in dim:
                                        original_name = dim["instance_name"]
                                        dim["instance_name"] = self._normalize_instance_name(original_name)
                                        if original_name != dim["instance_name"]:
                                            logger.debug(f"Normalized instance_name: '{original_name}' -> '{dim['instance_name']}'")
                                    
                                    # Normalize entity references in relations (hasEntities, directRelations, relatedTo, hasExpressor, identifiedAs, manifestsToxicity)
                                    # Note: _normalize_entity_references modifies the dict in place
                                    self._normalize_entity_references(dim)
                        
                        if dimensions:  # Non-empty list
                            extracted_dimensions.extend(dimensions)
                            extraction_metadata["dimensions_processed"].append(dimension_name)
                            logger.info(f"Extracted {len(dimensions)} instances for dimension: {dimension_name}")
                            
                            # Print terminal output for key dimensions
                            if dimension_name in ["TextualMaterial", "VisualMaterial", "BackgroundKnowledge", "Scene"]:
                                self._print_dimension_output(dimension_name, dimensions)
                        else:  # Empty list
                            logger.warning(f"Extracted 0 instances for dimension: {dimension_name} (empty result)")
                            extraction_metadata["dimensions_processed"].append(dimension_name)
                        
                        # Store VisualMaterial entities for Scene and BackgroundKnowledge
                        # These are already normalized above
                        if dimension_name == "VisualMaterial" and dimensions:
                            visual_material_entities = dimensions
                            logger.info(f"Stored {len(visual_material_entities)} VisualMaterial entities")
                        
                        # Store TextualMaterial entities for BackgroundKnowledge
                        # These are already normalized above
                        if dimension_name == "TextualMaterial" and dimensions:
                            textual_material_entities = dimensions
                            logger.info(f"Stored {len(textual_material_entities)} TextualMaterial entities")
                        
                        # Store BackgroundKnowledge entities for AnalogicalMapping
                        # These are already normalized above
                        if dimension_name == "BackgroundKnowledge" and dimensions:
                            background_knowledge_entities = dimensions
                            logger.info(f"Stored {len(background_knowledge_entities)} BackgroundKnowledge entities")
                        
                        # Store AnalogicalMapping entities for ToxicityAssessment
                        # These are already normalized above
                        if dimension_name == "AnalogicalMapping" and dimensions:
                            metaphorical_mapping_entities = dimensions
                            logger.info(f"Stored {len(metaphorical_mapping_entities)} AnalogicalMapping entities")
                    else:
                        logger.error(f"Extraction returned None for dimension: {dimension_name}")
                    
                except Exception as e:
                    logger.error(f"Failed to extract dimension {dimension_name}: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                    continue
            
            # Update metadata
            extraction_metadata["total_dimensions_found"] = len(extracted_dimensions)
            
            # Create result
            result = {
                "dimensions": extracted_dimensions,
                "metadata": extraction_metadata,
                "success": True
            }
            
            # Save outputs if output directory specified
            if output_dir:
                saved_files = self._save_extraction_outputs(result, output_dir, image_path)
                result["saved_files"] = saved_files
            
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
        """Validate the input image path."""
        if not image_path.exists():
            raise ValueError(ErrorMessages.IMAGE_NOT_FOUND.format(path=image_path))
        
        if image_path.suffix.lower() not in PipelineConfig.SUPPORTED_IMAGE_FORMATS:
            raise ValueError(
                ErrorMessages.INVALID_IMAGE_FORMAT.format(
                    formats=PipelineConfig.SUPPORTED_IMAGE_FORMATS
                )
            )
    
    def _extract_single_dimension(
        self, 
        image_path: Path, 
        dimension_name: str, 
        prompt_data: Dict[str, Any],
        visual_material_entities: Optional[List[Dict[str, Any]]] = None,
        textual_material_entities: Optional[List[Dict[str, Any]]] = None,
        background_knowledge_entities: Optional[List[Dict[str, Any]]] = None,
        metaphorical_mapping_entities: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Extract instances for a single dimension using its prompt file.
        
        Args:
            image_path: Path to the image
            dimension_name: Name of the dimension
            prompt_data: Prompt data from JSON-LD file
            visual_material_entities: Optional list of VisualMaterial entities for Scene
            
        Returns:
            List of extracted dimension instances
        """
        # Get the extraction prompt
        extraction_prompt = prompt_data.get("promptExtractionText", "")
        if not extraction_prompt:
            logger.warning(f"No extraction prompt found for dimension: {dimension_name}")
            return []
        
        # Create the full prompt
        full_prompt = self._create_extraction_prompt(
            extraction_prompt, 
            prompt_data, 
            dimension_name,
            visual_material_entities=visual_material_entities,
            textual_material_entities=textual_material_entities,
            background_knowledge_entities=background_knowledge_entities,
            metaphorical_mapping_entities=metaphorical_mapping_entities
        )
        
        # Generate response using LLM
        try:
            response = self.llm_manager.generate_response(
                full_prompt, 
                image_path, 
                provider=self.llm_provider
            )
            
            # Parse the response
            dimensions = self._parse_extraction_response(response, dimension_name, prompt_data)
            
            return dimensions
            
        except Exception as e:
            logger.error(f"LLM extraction failed for dimension {dimension_name}: {e}")
            return []
    
    def _create_extraction_prompt(
        self, 
        base_prompt: str, 
        prompt_data: Dict[str, Any],
        dimension_name: str,
        visual_material_entities: Optional[List[Dict[str, Any]]] = None,
        textual_material_entities: Optional[List[Dict[str, Any]]] = None,
        background_knowledge_entities: Optional[List[Dict[str, Any]]] = None,
        metaphorical_mapping_entities: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        Create the full extraction prompt for a dimension.
        
        Args:
            base_prompt: Base prompt from JSON-LD file
            prompt_data: Complete prompt data
            dimension_name: Name of the dimension being extracted
            visual_material_entities: Optional list of VisualMaterial entities for Scene
            
        Returns:
            Complete extraction prompt
        """
        # Add dimension context
        dimension_label = prompt_data.get("rdfs:label", "Unknown Dimension")
        dimension_comment = prompt_data.get("rdfs:comment", "")
        
        # For Scene, add VisualMaterial entities context
        if dimension_name == "Scene" and visual_material_entities:
            entities_context = "\n\nVisual Material entities found in the image (use only these entity names exactly as shown):\n"
            for i, entity in enumerate(visual_material_entities, 1):
                instance_name = entity.get("instance_name", f"entity_{i}")
                label = entity.get("label", "unknown entity")
                description = entity.get("description", "")
                entities_context += f"- {instance_name}: {label} ({description})\n"
            
            # Create the full prompt with entities
            full_prompt = f"""You are analyzing a meme image to extract {dimension_label} dimensions.

Dimension: {dimension_label}
Description: {dimension_comment}
{entities_context}

{base_prompt}

IMPORTANT: 
- Use only the VisualMaterial entity names provided above (e.g., use "people", "water", "text" exactly as shown).
- You MUST return at least one scene showing how these entities relate to each other.
- Each scene should have hasEntities and directRelations.
- Do not return an empty array. Always create at least one scene.

Please analyze the image and provide your response in the exact JSON format specified in the prompt above. Be thorough and accurate in your analysis."""
        
        # For BackgroundKnowledge, add VisualMaterial and TextualMaterial entities context
        elif dimension_name == "BackgroundKnowledge" and (visual_material_entities or textual_material_entities):
            entities_context = "\n\nEntities found in the image (link BackgroundKnowledge to these using relatedTo):\n"
            
            if visual_material_entities:
                entities_context += "\nVisual Material entities:\n"
                for i, entity in enumerate(visual_material_entities, 1):
                    instance_name = entity.get("instance_name", f"entity_{i}")
                    label = entity.get("label", "unknown entity")
                    description = entity.get("description", "")
                    entities_context += f"- {instance_name}: {label} ({description})\n"
            
            if textual_material_entities:
                entities_context += "\nTextual Material entities:\n"
                for i, entity in enumerate(textual_material_entities, 1):
                    instance_name = entity.get("instance_name", f"entity_{i}")
                    label = entity.get("label", "unknown entity")
                    description = entity.get("description", "")
                    entities_context += f"- {instance_name}: {label} ({description})\n"
            
            # Create the full prompt with entities
            full_prompt = f"""You are analyzing a meme image to extract {dimension_label} dimensions.

Dimension: {dimension_label}
Description: {dimension_comment}

IMPORTANT: Background Knowledge refers to pieces of knowledge OUTSIDE the image that are needed to understand the meme. These are real-world entities, events, concepts, or references that are implicitly referred to but NOT directly visible in the image. Examples:
- Actor/character names (if a person in the image resembles a known actor)
- Historical events (if the scene references a historical event)
- Countries, political parties, art movements
- Cultural phenomena, social trends, or any real-world knowledge implicitly referenced

{entities_context}

{base_prompt}

IMPORTANT: 
- Focus ONLY on knowledge OUTSIDE the image, NOT what is directly visible.
- Use only the entity names provided above (e.g., use "people", "water", "text_chunk" exactly as shown).
- For each BackgroundKnowledge item, add relatedTo linking to VisualMaterial or TextualMaterial entities that require this external knowledge to be understood.
- You MUST include relatedTo relations for at least some BackgroundKnowledge items.

Please analyze the image and provide your response in the exact JSON format specified in the prompt above. Be thorough and accurate in your analysis."""
        
        # For EmotionExpression, add VisualMaterial and TextualMaterial entities context
        elif dimension_name == "EmotionExpression" and (visual_material_entities or textual_material_entities):
            entities_context = "\n\nEntities found in the image (link emotions to these expressors using hasExpressor):\n"
            
            if visual_material_entities:
                entities_context += "\nVisual Material entities:\n"
                for i, entity in enumerate(visual_material_entities, 1):
                    instance_name = entity.get("instance_name", f"entity_{i}")
                    label = entity.get("label", "unknown entity")
                    description = entity.get("description", "")
                    entities_context += f"- {instance_name}: {label} ({description})\n"
            
            if textual_material_entities:
                entities_context += "\nTextual Material entities:\n"
                for i, entity in enumerate(textual_material_entities, 1):
                    instance_name = entity.get("instance_name", f"entity_{i}")
                    label = entity.get("label", "unknown entity")
                    description = entity.get("description", "")
                    entities_context += f"- {instance_name}: {label} ({description})\n"
            
            # Create the full prompt with entities
            full_prompt = f"""You are analyzing a meme image to extract {dimension_label} dimensions.

Dimension: {dimension_label}
Description: {dimension_comment}

{entities_context}

{base_prompt}

IMPORTANT: 
- Extract emotions present in the image (e.g., 'mischievousness', 'concern', 'happiness', 'anger').
- Use only the entity names provided above (e.g., use "person", "text_chunk", "smile" exactly as shown).
- For each emotion extracted, create a hasExpressor relation linking the emotion to the VisualMaterial or TextualMaterial entity that expresses it.
- The hasExpressor field should be an array of objects with "entity" and "relation" keys: [{{"entity": "entity_name", "relation": "hasExpressor"}}]
- You MUST include hasExpressor relations for each emotion, linking it to the entity that expresses it.
- If an emotion is expressed by multiple entities, include all of them in the hasExpressor array.

Please analyze the image and provide your response in the exact JSON format specified in the prompt above. Be thorough and accurate in your analysis."""
        
        # For AnalogicalMapping, add VisualMaterial, TextualMaterial, and BackgroundKnowledge entities context
        elif dimension_name == "AnalogicalMapping" and (visual_material_entities or textual_material_entities or background_knowledge_entities):
            entities_context = "\n\nEntities found in the image (use these to identify metaphorical mappings):\n"
            
            if visual_material_entities:
                entities_context += "\nVisual Material entities:\n"
                for i, entity in enumerate(visual_material_entities, 1):
                    instance_name = entity.get("instance_name", f"entity_{i}")
                    label = entity.get("label", "unknown entity")
                    description = entity.get("description", "")
                    entities_context += f"- {instance_name}: {label} ({description})\n"
            
            if textual_material_entities:
                entities_context += "\nTextual Material entities:\n"
                for i, entity in enumerate(textual_material_entities, 1):
                    instance_name = entity.get("instance_name", f"entity_{i}")
                    label = entity.get("label", "unknown entity")
                    description = entity.get("description", "")
                    entities_context += f"- {instance_name}: {label} ({description})\n"
            
            if background_knowledge_entities:
                entities_context += "\nBackground Knowledge entities:\n"
                for i, entity in enumerate(background_knowledge_entities, 1):
                    instance_name = entity.get("instance_name", f"entity_{i}")
                    label = entity.get("label", "unknown entity")
                    description = entity.get("description", "")
                    entities_context += f"- {instance_name}: {label} ({description})\n"
            
            # Create the full prompt with entities
            full_prompt = f"""You are analyzing a meme image to extract {dimension_label} dimensions.

Dimension: {dimension_label}
Description: {dimension_comment}

{entities_context}

{base_prompt}

IMPORTANT: 
- Identify metaphorical and analogical mappings between textual material and visual material.
- The task is to identify when a textual element (e.g., "me", or some other entity referred to in the textual material) is projected onto a visual element.
- This can happen through spatial adjacency, text positioning, or other contextual cues.
- For each mapping found, create an "identifiedAs" relation linking the textual entity to the visual entity.
- The identifiedAs field should be an array of objects with "entity" and "relation" keys: [{{"entity": "visual_entity_name", "relation": "identifiedAs"}}]
- Use only the entity names provided above (e.g., use "person", "text_chunk", "me" exactly as shown).
- If a textual element is identified as multiple visual elements, include all of them in the identifiedAs array.
- Focus on clear cases where text explicitly or implicitly identifies something as something else in the visual material.

Please analyze the image and provide your response in the exact JSON format specified in the prompt above. Be thorough and accurate in your analysis."""
        
        # For ToxicityAssessment, add VisualMaterial, TextualMaterial, BackgroundKnowledge, and AnalogicalMapping entities context
        elif dimension_name == "ToxicityAssessment" and (visual_material_entities or textual_material_entities or background_knowledge_entities or metaphorical_mapping_entities):
            entities_context = "\n\nEntities found in the image (assess toxicity for these):\n"
            
            if visual_material_entities:
                entities_context += "\nVisual Material entities:\n"
                for i, entity in enumerate(visual_material_entities, 1):
                    instance_name = entity.get("instance_name", f"entity_{i}")
                    label = entity.get("label", "unknown entity")
                    description = entity.get("description", "")
                    entities_context += f"- {instance_name}: {label} ({description})\n"
            
            if textual_material_entities:
                entities_context += "\nTextual Material entities:\n"
                for i, entity in enumerate(textual_material_entities, 1):
                    instance_name = entity.get("instance_name", f"entity_{i}")
                    label = entity.get("label", "unknown entity")
                    description = entity.get("description", "")
                    entities_context += f"- {instance_name}: {label} ({description})\n"
            
            if background_knowledge_entities:
                entities_context += "\nBackground Knowledge entities:\n"
                for i, entity in enumerate(background_knowledge_entities, 1):
                    instance_name = entity.get("instance_name", f"entity_{i}")
                    label = entity.get("label", "unknown entity")
                    description = entity.get("description", "")
                    entities_context += f"- {instance_name}: {label} ({description})\n"
            
            if metaphorical_mapping_entities:
                entities_context += "\nMetaphorical and Analogical Mapping entities:\n"
                for i, entity in enumerate(metaphorical_mapping_entities, 1):
                    instance_name = entity.get("instance_name", f"entity_{i}")
                    label = entity.get("label", "unknown entity")
                    description = entity.get("description", "")
                    identified_as = entity.get("identifiedAs", [])
                    if identified_as:
                        identified_entities = ", ".join([rel.get("entity", "") for rel in identified_as if isinstance(rel, dict)])
                        entities_context += f"- {instance_name}: {label} ({description}) [identifiedAs: {identified_entities}]\n"
                    else:
                        entities_context += f"- {instance_name}: {label} ({description})\n"
            
            # Create the full prompt with entities
            full_prompt = f"""You are analyzing a meme image to extract {dimension_label} dimensions.

Dimension: {dimension_label}
Description: {dimension_comment}

{entities_context}

{base_prompt}

IMPORTANT: 
- Assess toxicity for entities from VisualMaterial, TextualMaterial, BackgroundKnowledge, and AnalogicalMapping.
- Identify toxicity types from these categories:
  * Abusive: memes used to threaten and abuse individuals or specific target communities. They contain words that target individuals or different protected communities, implicitly containing hateful, harmful, and antisemitic content.
  * Cyberbulling: memes that disparage an individual based on characteristics such as color, gender, race, sexual orientation, ethnicity, nationality, or other features.
  * Harmful: memes that "have the potential to cause harm to an individual, an organization, a community, or the society more generally. Harm includes mental abuse, defamation, psycho-physiological injury, proprietary damage, emotional disturbance.
  * Hateful: memes characterized as direct or indirect attacks on individuals based on protected characteristics such as ethnicity, race, nationality, immigration status, religion, caste, sex, gender identity, sexual orientation, disability, or disease. An attack is defined as containing violent or dehumanizing speech, statements of inferiority, or calls for exclusion or segregation.
  * Mysogynous: memes containing hate against women.
  * Propaganda: memes to influence the opinions or actions of people toward a specific goal.
- For each entity that manifests toxicity, create a manifestsToxicity relation linking the entity to the toxicity type.
- The manifestsToxicity field should be an array of objects with "entity" and "relation" keys: [{{"entity": "toxicity_type", "relation": "manifestsToxicity"}}]
- Use only the entity names provided above (e.g., use "person", "text_chunk", "mapping" exactly as shown).
- Use the exact toxicity type names: Abusive, Cyberbulling, Harmful, Hateful, Mysogynous, or Propaganda.
- If an entity manifests multiple types of toxicity, include all of them in the manifestsToxicity array.
- If no toxicity is found, return an empty array.

Please analyze the image and provide your response in the exact JSON format specified in the prompt above. Be thorough and accurate in your analysis."""
        else:
            # Create the full prompt without entities
            full_prompt = f"""You are analyzing a meme image to extract {dimension_label} dimensions.

Dimension: {dimension_label}
Description: {dimension_comment}

{base_prompt}

Please analyze the image and provide your response in the exact JSON format specified in the prompt above. Be thorough and accurate in your analysis."""

        return full_prompt
    
    def _parse_extraction_response(
        self, 
        response: str, 
        dimension_name: str, 
        prompt_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Parse the LLM response to extract dimension data.
        
        Args:
            response: Raw LLM response
            dimension_name: Name of the dimension
            prompt_data: Prompt data for context
            
        Returns:
            List of parsed dimension instances
        """
        dimensions = []
        
        try:
            # Try to extract JSON from the response
            json_data = self._extract_json_from_response(response)
            
            # Debug logging for Scene
            if dimension_name == "Scene":
                logger.info(f"Scene raw response: {response[:500]}...")
                logger.info(f"Scene parsed JSON: {json_data}")
                logger.info(f"Scene JSON type: {type(json_data)}")
            
            if isinstance(json_data, list):
                # Multiple dimensions
                for item in json_data:
                    # Normalize entity references BEFORE creating dimension instance
                    item = self._normalize_entity_references(item)
                    dimension_instances = self._create_dimension_instance(item, dimension_name, prompt_data)
                    if dimension_instances:
                        if isinstance(dimension_instances, list):
                            dimensions.extend(dimension_instances)
                        else:
                            dimensions.append(dimension_instances)
            elif isinstance(json_data, dict):
                # Single dimension
                # Normalize entity references BEFORE creating dimension instance
                json_data = self._normalize_entity_references(json_data)
                dimension_instances = self._create_dimension_instance(json_data, dimension_name, prompt_data)
                if dimension_instances:
                    if isinstance(dimension_instances, list):
                        dimensions.extend(dimension_instances)
                    else:
                        dimensions.append(dimension_instances)
            
        except Exception as e:
            logger.warning(f"Failed to parse response for dimension {dimension_name}: {e}")
            # Try to extract dimensions using regex as fallback
            dimensions = self._extract_dimensions_with_regex(response, dimension_name, prompt_data)
        
        return dimensions
    
    def _extract_json_from_response(self, response: str) -> Any:
        """Extract JSON data from LLM response with enhanced parsing for llama3.2-vision."""
        import re
        
        # Enhanced patterns for llama3.2-vision responses
        json_patterns = [
            r'```json\s*(.*?)\s*```',
            r'```\s*(.*?)\s*```',
            r'\{[^{}]*"instance_name"[^{}]*\}',  # Look for specific JSON structure
            r'\{.*\}',
            r'\[.*\]'
        ]
        
        # Try each pattern
        for pattern in json_patterns:
            matches = re.findall(pattern, response, re.DOTALL)
            for match in matches:
                try:
                    cleaned_match = match.strip()
                    # Remove any trailing text after the JSON
                    if cleaned_match.count('{') > cleaned_match.count('}'):
                        # Try to find the complete JSON object
                        brace_count = 0
                        end_pos = 0
                        for i, char in enumerate(cleaned_match):
                            if char == '{':
                                brace_count += 1
                            elif char == '}':
                                brace_count -= 1
                                if brace_count == 0:
                                    end_pos = i + 1
                                    break
                        if end_pos > 0:
                            cleaned_match = cleaned_match[:end_pos]
                    
                    return json.loads(cleaned_match)
                except json.JSONDecodeError:
                    continue
        
        # Try to extract JSON from lines that look like JSON
        lines = response.split('\n')
        json_lines = []
        in_json = False
        brace_count = 0
        
        for line in lines:
            line = line.strip()
            if line.startswith('{') or in_json:
                json_lines.append(line)
                brace_count += line.count('{') - line.count('}')
                if brace_count == 0 and line.endswith('}'):
                    try:
                        json_text = '\n'.join(json_lines)
                        return json.loads(json_text)
                    except json.JSONDecodeError:
                        json_lines = []
                        in_json = False
                        continue
                in_json = True
        
        # If no JSON found, try parsing the entire response
        try:
            return json.loads(response.strip())
        except json.JSONDecodeError:
            raise ValueError("No valid JSON found in response")
    
    def _normalize_instance_name(self, name: str) -> str:
        """
        Normalize instance names to ensure only underscores are used.
        
        Replaces all special characters (except underscores) with underscores,
        removes multiple consecutive underscores, and trims underscores from ends.
        
        Args:
            name: Original instance name
            
        Returns:
            Normalized instance name safe for URIs
        """
        if not isinstance(name, str):
            name = str(name)
        
        # Replace all special characters with underscores
        import re
        # Replace spaces, hyphens, parentheses, and other special chars with underscore
        normalized = re.sub(r'[^\w]', '_', name)
        # Replace multiple consecutive underscores with single underscore
        normalized = re.sub(r'_+', '_', normalized)
        # Remove underscores from start and end
        normalized = normalized.strip('_')
        # Ensure it's not empty
        if not normalized:
            normalized = 'unnamed'
        
        return normalized
    
    def _normalize_entity_references(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize all entity references in dimension data (instance_name, hasEntities, directRelations, relatedTo, hasExpressor, identifiedAs, manifestsToxicity).
        
        Args:
            data: Dimension data dictionary
            
        Returns:
            Normalized dimension data
        """
        # Normalize instance_name
        if "instance_name" in data:
            data["instance_name"] = self._normalize_instance_name(data["instance_name"])
        
        # Normalize hasEntities (Scene)
        if "hasEntities" in data and isinstance(data["hasEntities"], list):
            for entity in data["hasEntities"]:
                if isinstance(entity, dict) and "entity" in entity:
                    entity["entity"] = self._normalize_instance_name(entity["entity"])
        
        # Normalize directRelations (Scene)
        if "directRelations" in data and isinstance(data["directRelations"], list):
            for rel in data["directRelations"]:
                if isinstance(rel, dict):
                    if "from" in rel:
                        rel["from"] = self._normalize_instance_name(rel["from"])
                    if "to" in rel:
                        rel["to"] = self._normalize_instance_name(rel["to"])
        
        # Normalize relatedTo (BackgroundKnowledge)
        if "relatedTo" in data and isinstance(data["relatedTo"], list):
            for rel in data["relatedTo"]:
                if isinstance(rel, dict) and "entity" in rel:
                    rel["entity"] = self._normalize_instance_name(rel["entity"])
        
        # Normalize hasExpressor (EmotionExpression)
        if "hasExpressor" in data and isinstance(data["hasExpressor"], list):
            for rel in data["hasExpressor"]:
                if isinstance(rel, dict) and "entity" in rel:
                    rel["entity"] = self._normalize_instance_name(rel["entity"])
        
        # Normalize identifiedAs (AnalogicalMapping)
        if "identifiedAs" in data and isinstance(data["identifiedAs"], list):
            for rel in data["identifiedAs"]:
                if isinstance(rel, dict) and "entity" in rel:
                    rel["entity"] = self._normalize_instance_name(rel["entity"])
        
        # Normalize manifestsToxicity (ToxicityAssessment)
        if "manifestsToxicity" in data and isinstance(data["manifestsToxicity"], list):
            for rel in data["manifestsToxicity"]:
                if isinstance(rel, dict) and "entity" in rel:
                    rel["entity"] = self._normalize_instance_name(rel["entity"])
        
        return data
    
    def _create_dimension_instance(
        self, 
        data: Dict[str, Any], 
        dimension_name: str, 
        prompt_data: Dict[str, Any]
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Create a dimension instance from parsed data.
        
        Args:
            data: Parsed dimension data
            dimension_name: Name of the dimension
            prompt_data: Prompt data for context
            
        Returns:
            List of formatted dimension instances or None if invalid
        """
        try:
            formatted_instances = []
            
            # Debug logging for Scene
            if dimension_name == "Scene":
                logger.info(f"Scene _create_dimension_instance called with data: {data}")
                logger.info(f"Scene data keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
            
            # Universal dimension instance creation - works for all formats
            # Strategy 1: Direct format (has instance_name, label, and optionally description)
            if "instance_name" in data and "label" in data:
                # Use provided description or build from other fields
                if "description" in data:
                    description = data["description"]
                else:
                    # Build description from available fields
                    description_parts = []
                    for key, value in data.items():
                        if key not in ['instance_name', 'label', 'confidence', '@context', '@type', '@id', 'hasEntities', 'directRelations', 'relatedTo', 'hasExpressor', 'identifiedAs', 'manifestsToxicity']:
                            if isinstance(value, list):
                                description_parts.append(f"{key}: {', '.join(map(str, value))}")
                            else:
                                description_parts.append(f"{key}: {value}")
                    description = "; ".join(description_parts) if description_parts else f"Generic {dimension_name} instance"
                
                dimension = {
                    "class_name": dimension_name,
                    "class_uri": prompt_data.get("@id", f"http://example.org/multimodal-taxonomy#{dimension_name}"),
                    "instance_name": data["instance_name"],
                    "label": data["label"],
                    "description": description,
                    "extraction_method": f"claude_api_with_jsonld_prompts_{self.llm_manager.get_current_model()}",
                    # "confidence": data.get("confidence", 0.8),  # Commented out - hardcoded default not meaningful
                    "dimension_index": prompt_data.get("dimensionIndex", 0)
                }
                
                # For Scene, preserve frame-based relations
                if dimension_name == "Scene":
                    if "hasEntities" in data:
                        dimension["hasEntities"] = data["hasEntities"]
                    if "directRelations" in data:
                        dimension["directRelations"] = data["directRelations"]
                
                # For BackgroundKnowledge, preserve relatedTo relations
                if dimension_name == "BackgroundKnowledge":
                    if "relatedTo" in data:
                        dimension["relatedTo"] = data["relatedTo"]
                
                # For EmotionExpression, preserve hasExpressor relations
                if dimension_name == "EmotionExpression":
                    if "hasExpressor" in data:
                        dimension["hasExpressor"] = data["hasExpressor"]
                
                # For AnalogicalMapping, preserve identifiedAs relations
                if dimension_name == "AnalogicalMapping":
                    if "identifiedAs" in data:
                        dimension["identifiedAs"] = data["identifiedAs"]
                
                # For ToxicityAssessment, preserve manifestsToxicity relations
                if dimension_name == "ToxicityAssessment":
                    if "manifestsToxicity" in data:
                        dimension["manifestsToxicity"] = data["manifestsToxicity"]
                
                formatted_instances.append(dimension)
            
            # Strategy 2: List format (arrays of elements)
            elif any(key.endswith("_elements") or key.endswith("Elements") for key in data.keys()):
                for key in data.keys():
                    if key.endswith("_elements") or key.endswith("Elements"):
                        elements = data[key]
                        if isinstance(elements, list):
                            for i, element in enumerate(elements):
                                if isinstance(element, dict):
                                    instance_name = element.get("instance_name", f"{dimension_name.lower()}_{i+1}")
                                    label = element.get("label", element.get("name", f"the {dimension_name.lower()} element"))
                                    description = element.get("description", element.get("text", "No description available"))
                                    
                                    dimension = {
                                        "class_name": dimension_name,
                                        "class_uri": prompt_data.get("@id", f"http://example.org/multimodal-taxonomy#{dimension_name}"),
                                        "instance_name": instance_name,
                                        "label": label,
                                        "description": description,
                                        "extraction_method": f"claude_api_with_jsonld_prompts_{self.llm_manager.get_current_model()}",
                                        # "confidence": element.get("confidence", 0.8),  # Commented out - hardcoded default not meaningful
                                        "dimension_index": prompt_data.get("dimensionIndex", 0)
                                    }
                                    formatted_instances.append(dimension)
            
            # Strategy 3: Single object with custom fields (like Scene)
            else:
                # Extract instance_name and label with fallbacks
                instance_name = data.get("instance_name", f"{dimension_name.lower()}_instance")
                label = data.get("label", f"the {dimension_name.lower()}")
                
                # Build description from available fields
                description_parts = []
                for key, value in data.items():
                    if key not in ['instance_name', 'label', 'confidence', '@context', '@type', '@id', 'hasEntities', 'directRelations']:
                        if isinstance(value, list):
                            description_parts.append(f"{key}: {', '.join(map(str, value))}")
                        else:
                            description_parts.append(f"{key}: {value}")
                
                description = "; ".join(description_parts) if description_parts else f"Generic {dimension_name} instance"
                
                dimension = {
                    "class_name": dimension_name,
                    "class_uri": prompt_data.get("@id", f"http://example.org/multimodal-taxonomy#{dimension_name}"),
                    "instance_name": instance_name,
                    "label": label,
                    "description": description,
                    "extraction_method": f"claude_api_with_jsonld_prompts_{self.llm_manager.get_current_model()}",
                    # "confidence": data.get("confidence", 0.8),  # Commented out - hardcoded default not meaningful
                    "dimension_index": prompt_data.get("dimensionIndex", 0)
                }
                
                # For Scene, preserve frame-based relations
                if dimension_name == "Scene":
                    if "hasEntities" in data:
                        dimension["hasEntities"] = data["hasEntities"]
                    if "directRelations" in data:
                        dimension["directRelations"] = data["directRelations"]
                
                # For BackgroundKnowledge, preserve relatedTo relations
                if dimension_name == "BackgroundKnowledge":
                    if "relatedTo" in data:
                        dimension["relatedTo"] = data["relatedTo"]
                
                # For EmotionExpression, preserve hasExpressor relations
                if dimension_name == "EmotionExpression":
                    if "hasExpressor" in data:
                        dimension["hasExpressor"] = data["hasExpressor"]
                
                # For AnalogicalMapping, preserve identifiedAs relations
                if dimension_name == "AnalogicalMapping":
                    if "identifiedAs" in data:
                        dimension["identifiedAs"] = data["identifiedAs"]
                
                # For ToxicityAssessment, preserve manifestsToxicity relations
                if dimension_name == "ToxicityAssessment":
                    if "manifestsToxicity" in data:
                        dimension["manifestsToxicity"] = data["manifestsToxicity"]
                
                formatted_instances.append(dimension)
            
            # Debug logging for Scene
            if dimension_name == "Scene":
                logger.info(f"Scene returning {len(formatted_instances)} instances: {formatted_instances}")
            
            return formatted_instances if formatted_instances else None
            
        except Exception as e:
            logger.error(f"Error creating dimension instance: {e}")
            return None
    
    def _convert_generic_json_to_dimensions(self, data: Dict[str, Any], dimension_name: str, prompt_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Convert any generic JSON structure to dimension instances.
        This is a flexible fallback that tries to extract meaningful dimension data from any valid JSON.
        
        Args:
            data: Generic JSON data from LLM
            dimension_name: Name of the dimension
            prompt_data: Prompt data for context
            
        Returns:
            List of formatted dimension instances
        """
        formatted_instances = []
        
        try:
            # Strategy 1: Look for arrays of objects (most common pattern)
            for key, value in data.items():
                if isinstance(value, list) and value:
                    # Check if it's an array of objects
                    if all(isinstance(item, dict) for item in value):
                        for i, item in enumerate(value):
                            # Try to extract meaningful fields
                            instance_name = self._extract_field(item, ['instance_name', 'name', 'id', 'emotion_name', 'expressor'], f"{dimension_name.lower()}_{i+1}")
                            label = self._extract_field(item, ['label', 'title', 'name', 'emotion_name'], f"the {dimension_name.lower()} element")
                            description = self._extract_field(item, ['description', 'text', 'content', 'relationship'], "No description available")
                            
                            dimension = {
                                "class_name": dimension_name,
                                "class_uri": prompt_data.get("@id", f"http://example.org/multimodal-taxonomy#{dimension_name}"),
                                "instance_name": instance_name,
                                "label": label,
                                "description": description,
                                "extraction_method": f"claude_api_with_jsonld_prompts_{self.llm_manager.get_current_model()}",
                                # "confidence": item.get("confidence", 0.8),  # Commented out - hardcoded default not meaningful
                                "dimension_index": prompt_data.get("dimensionIndex", 0)
                            }
                            formatted_instances.append(dimension)
            
            # Strategy 2: If no arrays found, treat the whole object as a single dimension
            if not formatted_instances:
                # Extract meaningful fields from the root object
                instance_name = self._extract_field(data, ['instance_name', 'name', 'id', '@type'], f"{dimension_name.lower()}_instance")
                label = self._extract_field(data, ['label', 'title', 'name'], f"the {dimension_name.lower()}")
                description = self._extract_field(data, ['description', 'text', 'content', 'comment'], "No description available")
                
                # If no description found, create one from available data
                if description == "No description available":
                    description_parts = []
                    for key, value in data.items():
                        if key not in ['@context', '@type', '@id'] and isinstance(value, (str, int, float)):
                            description_parts.append(f"{key}: {value}")
                    description = "; ".join(description_parts) if description_parts else f"Generic {dimension_name} instance"
                
                dimension = {
                    "class_name": dimension_name,
                    "class_uri": prompt_data.get("@id", f"http://example.org/multimodal-taxonomy#{dimension_name}"),
                    "instance_name": instance_name,
                    "label": label,
                    "description": description,
                    "extraction_method": f"claude_api_with_jsonld_prompts_{self.llm_manager.get_current_model()}",
                    # "confidence": data.get("confidence", 0.8),  # Commented out - hardcoded default not meaningful
                    "dimension_index": prompt_data.get("dimensionIndex", 0)
                }
                formatted_instances.append(dimension)
            
            logger.info(f"Converted {len(formatted_instances)} dimension instances from generic JSON for {dimension_name}")
            return formatted_instances
            
        except Exception as e:
            logger.error(f"Error converting generic JSON to dimensions: {e}")
            return []
    
    def _extract_field(self, data: Dict[str, Any], field_candidates: List[str], default: str) -> str:
        """
        Extract a field value from data using multiple possible field names.
        
        Args:
            data: Dictionary to search in
            field_candidates: List of possible field names to try
            default: Default value if no field is found
            
        Returns:
            Extracted field value or default
        """
        for candidate in field_candidates:
            if candidate in data and data[candidate]:
                return str(data[candidate])
        return default
    
    def _extract_dimensions_with_regex(
        self, 
        response: str, 
        dimension_name: str, 
        prompt_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Extract dimensions using regex patterns as fallback."""
        import re
        
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
                    "class_name": dimension_name,
                    "class_uri": prompt_data.get("@id", f"http://example.org/multimodal-taxonomy#{dimension_name}"),
                    "instance_name": instance_names[i] if i < len(instance_names) else f"dimension_{i+1}",
                    "label": labels[i] if i < len(labels) else f"the {dimension_name.lower()}",
                    "description": descriptions[i] if i < len(descriptions) else "Extracted from image analysis",
                    "extraction_method": "regex_fallback",
                    # "confidence": 0.5,  # Commented out - hardcoded default not meaningful
                    "dimension_index": prompt_data.get("dimensionIndex", 0)
                }
                dimensions.append(dimension)
            except Exception as e:
                logger.warning(f"Error creating fallback dimension {i}: {e}")
                continue
        
        return dimensions
    
    def _print_dimension_output(self, dimension_name: str, dimensions: List[Dict[str, Any]]) -> None:
        """
        Print dimension output to terminal in a formatted way.
        
        Args:
            dimension_name: Name of the dimension (e.g., "TextualMaterial")
            dimensions: List of extracted dimension instances
        """
        print(f"\n{'='*70}")
        print(f"📋 {dimension_name} Entities ({len(dimensions)} found)")
        print(f"{'='*70}")
        
        for i, dim in enumerate(dimensions, 1):
            instance_name = dim.get("instance_name", "unknown")
            label = dim.get("label", "N/A")
            description = dim.get("description", "N/A")
            
            print(f"\n  {i}. {instance_name}")
            print(f"     Label: {label}")
            if description and description != label:
                # Truncate long descriptions
                desc = description[:200] + "..." if len(description) > 200 else description
                print(f"     Description: {desc}")
            
            # Special handling for Scene with frame-based relations
            if dimension_name == "Scene":
                if "hasEntities" in dim and dim["hasEntities"]:
                    print(f"     Scene → Entity Relations:")
                    for rel in dim["hasEntities"]:
                        relation = rel.get("relation", "unknown")
                        entity = rel.get("entity", "unknown")
                        print(f"       • {relation}: {entity}")
                
                if "directRelations" in dim and dim["directRelations"]:
                    print(f"     Entity → Entity Relations:")
                    for rel in dim["directRelations"]:
                        from_entity = rel.get("from", "unknown")
                        relation = rel.get("relation", "unknown")
                        to_entity = rel.get("to", "unknown")
                        print(f"       • {from_entity} {relation} {to_entity}")
            
            # Special handling for BackgroundKnowledge with relatedTo relations
            if dimension_name == "BackgroundKnowledge":
                if "relatedTo" in dim and dim["relatedTo"]:
                    print(f"     BackgroundKnowledge → Entity Relations:")
                    for rel in dim["relatedTo"]:
                        relation = rel.get("relation", "relatedTo")
                        entity = rel.get("entity", "unknown")
                        print(f"       • {relation}: {entity}")
        
        print(f"{'='*70}\n")
    
    def _save_extraction_outputs(
        self, 
        result: Dict[str, Any], 
        output_dir: Path,
        image_path: Path
    ) -> Dict[str, Path]:
        """
        Save extraction results to files.
        
        Args:
            result: Extraction results
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
            if result["success"] and result["dimensions"]:
                jsonld_doc = self.jsonld_handler.create_dimensions_jsonld(
                    result["dimensions"], 
                    image_path, 
                    result["metadata"]
                )
                
                jsonld_path = output_dir / f"{base_name}_dimensions.jsonld"
                self.jsonld_handler.save_jsonld(jsonld_doc, jsonld_path)
                saved_files["dimensions_jsonld"] = jsonld_path
                
                # Save individual dimension JSON-LD files in organized folder structure
                for dimension in result["dimensions"]:
                    dimension_name = dimension.get("class_name", "unknown")
                    instance_name = dimension.get("instance_name", "instance")
                    
                    # Create dimension-specific folder
                    dimension_dir = output_dir / "dimensions" / dimension_name
                    dimension_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Create individual JSON-LD document for this dimension
                    individual_jsonld = {
                        "@context": {
                            "@vocab": "http://example.org/multimodal-taxonomy#",
                            "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
                            "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
                            "owl": "http://www.w3.org/2002/07/owl#"
                        },
                        "@id": f"http://example.org/multimodal-taxonomy#{instance_name}",
                        "@type": dimension_name,
                        "instance_name": dimension["instance_name"],
                        "label": dimension["label"],
                        "description": dimension["description"],
                        "extractionMethod": dimension["extraction_method"],
                        # "confidence": dimension["confidence"],  # Commented out - confidence field removed
                        "extractedFrom": base_name,
                        "extractionTimestamp": result["metadata"]["extraction_timestamp"],
                        "belongsToAnalysis": {
                            "@id": f"http://example.org/multimodal-taxonomy#analysis_{result['metadata'].get('analysis_id', 'unknown')}"
                        }
                    }
                    
                    # Save individual dimension file in dimension-specific folder
                    individual_path = dimension_dir / f"{base_name}_{instance_name}.jsonld"
                    with open(individual_path, 'w', encoding='utf-8') as f:
                        json.dump(individual_jsonld, f, indent=2, ensure_ascii=False)
                    
                    # Track saved files
                    if f"{dimension_name}_individual" not in saved_files:
                        saved_files[f"{dimension_name}_individual"] = []
                    saved_files[f"{dimension_name}_individual"].append(str(individual_path))
                
                # Save raw JSON for debugging
                raw_json_path = output_dir / f"{base_name}_dimensions_raw.json"
                with open(raw_json_path, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)
                saved_files["raw_json"] = raw_json_path
            
            # Save enhanced TTL file
            ttl_path = output_dir / f"{base_name}_enhanced_ontology.ttl"
            self._save_enhanced_ttl(result, ttl_path)
            saved_files["enhanced_ttl"] = ttl_path
            
            # Save text summary
            text_path = output_dir / f"{base_name}_dimensions.txt"
            self._save_text_summary(result, text_path)
            saved_files["text_summary"] = text_path
            
            # Log individual dimension files
            for key, files in saved_files.items():
                if key.endswith("_individual") and isinstance(files, list):
                    dimension_name = key.replace("_individual", "")
                    logger.info(f"Saved {len(files)} individual {dimension_name} files in dimensions/{dimension_name}/")
            
            logger.info(f"Extraction results saved to: {output_dir}")
            return saved_files
            
        except Exception as e:
            logger.error(f"Failed to save extraction results: {e}")
            return {}
    
    def _save_enhanced_ttl(self, result: Dict[str, Any], output_path: Path) -> None:
        """
        Save enhanced TTL file with original ontology + extracted dimensions.
        
        Args:
            result: Extraction results
            output_path: Path to save the TTL file
        """
        try:
            # Read original ontology
            with open(self.ontology_path, 'r', encoding='utf-8') as f:
                original_ttl = f.read()
            
            # Safeguard: Check if ontology contains extracted individuals (contamination)
            if "extractionTimestamp" in original_ttl:
                logger.warning("⚠️  WARNING: Original ontology file contains extracted individuals!")
                logger.warning("⚠️  This may indicate contamination from previous runs.")
                logger.warning("⚠️  Consider cleaning the ontology file to remove extracted individuals.")
                # For now, we'll continue but log the issue
            
            # Create enhanced TTL content
            enhanced_ttl = original_ttl + "\n\n"
            enhanced_ttl += "#################################################################\n"
            enhanced_ttl += "#    Extracted Dimension Instances\n"
            enhanced_ttl += "#################################################################\n\n"
            
            # Collect directRelations from Scene to add as separate statements
            direct_relations_statements = []
            
            # Add extracted dimensions as TTL individuals
            # Note: instance_name should already be normalized (only underscores) from normalization step
            for dim in result["dimensions"]:
                # Double-check normalization (should already be done, but ensure it)
                instance_name = self._normalize_instance_name(dim["instance_name"])
                class_name = dim["class_name"]
                
                # Escape strings for TTL format
                def escape_ttl_string(text):
                    if not isinstance(text, str):
                        text = str(text)
                    # Escape quotes and backslashes
                    text = text.replace("\\", "\\\\")
                    text = text.replace('"', '\\"')
                    # Replace newlines with spaces
                    text = text.replace('\n', ' ').replace('\r', ' ')
                    # Truncate very long strings to prevent TTL parsing issues
                    if len(text) > 500:
                        text = text[:497] + "..."
                    return text
                
                enhanced_ttl += f"###  http://example.org/multimodal-taxonomy#{instance_name}\n"
                enhanced_ttl += f":{instance_name} rdf:type :{class_name} ;\n"
                enhanced_ttl += f"                rdfs:label \"{escape_ttl_string(dim['label'])}\"@en ;\n"
                enhanced_ttl += f"                rdfs:comment \"{escape_ttl_string(dim['description'])}\"@en ;\n"
                enhanced_ttl += f"                :extractionMethod \"{escape_ttl_string(dim['extraction_method'])}\" ;\n"
                # enhanced_ttl += f"                :confidence {dim.get('confidence', 0.8)} ;\n"  # Commented out - confidence field removed
                
                # Handle frame-based relations for Scene
                if class_name == "Scene":
                    # Add scene→entity relations (hasEntities)
                    if "hasEntities" in dim and dim["hasEntities"]:
                        for rel in dim["hasEntities"]:
                            relation = self._normalize_instance_name(rel.get("relation", ""))
                            entity = self._normalize_instance_name(rel.get("entity", ""))
                            if relation and entity:
                                enhanced_ttl += f"                :{relation} :{entity} ;\n"
                    
                    # Collect directRelations to add as separate statements later
                    if "directRelations" in dim and dim["directRelations"]:
                        for rel in dim["directRelations"]:
                            from_entity = self._normalize_instance_name(rel.get("from", ""))
                            relation = self._normalize_instance_name(rel.get("relation", ""))
                            to_entity = self._normalize_instance_name(rel.get("to", ""))
                            if from_entity and relation and to_entity:
                                # Store for later: these are entity→entity relations (not scene properties)
                                direct_relations_statements.append(
                                    f":{from_entity} :{relation} :{to_entity} ."
                                )
                
                # Handle relatedTo relations for BackgroundKnowledge
                if class_name == "BackgroundKnowledge":
                    # Collect relatedTo relations to add as separate statements later
                    if "relatedTo" in dim and dim["relatedTo"]:
                        for rel in dim["relatedTo"]:
                            entity = self._normalize_instance_name(rel.get("entity", ""))
                            relation = self._normalize_instance_name(rel.get("relation", "relatedTo"))
                            if instance_name and entity and relation:
                                # Store for later: these are BackgroundKnowledge→entity relations
                                direct_relations_statements.append(
                                    f":{instance_name} :{relation} :{entity} ."
                                )
                
                # Handle hasExpressor relations for EmotionExpression
                if class_name == "EmotionExpression":
                    # Collect hasExpressor relations to add as separate statements later
                    if "hasExpressor" in dim and dim["hasExpressor"]:
                        for rel in dim["hasExpressor"]:
                            entity = self._normalize_instance_name(rel.get("entity", ""))
                            relation = self._normalize_instance_name(rel.get("relation", "hasExpressor"))
                            if instance_name and entity and relation:
                                # Store for later: these are EmotionExpression→entity relations
                                direct_relations_statements.append(
                                    f":{instance_name} :{relation} :{entity} ."
                                )
                
                # Handle identifiedAs relations for AnalogicalMapping
                if class_name == "AnalogicalMapping":
                    # Collect identifiedAs relations to add as separate statements later
                    if "identifiedAs" in dim and dim["identifiedAs"]:
                        for rel in dim["identifiedAs"]:
                            entity = self._normalize_instance_name(rel.get("entity", ""))
                            relation = self._normalize_instance_name(rel.get("relation", "identifiedAs"))
                            if instance_name and entity and relation:
                                # Store for later: these are AnalogicalMapping→entity relations
                                direct_relations_statements.append(
                                    f":{instance_name} :{relation} :{entity} ."
                                )
                
                # Handle manifestsToxicity relations for ToxicityAssessment
                if class_name == "ToxicityAssessment":
                    # Collect manifestsToxicity relations to add as separate statements later
                    if "manifestsToxicity" in dim and dim["manifestsToxicity"]:
                        for rel in dim["manifestsToxicity"]:
                            entity = self._normalize_instance_name(rel.get("entity", ""))
                            relation = self._normalize_instance_name(rel.get("relation", "manifestsToxicity"))
                            if instance_name and entity and relation:
                                # Store for later: these are ToxicityAssessment→toxicity_type relations
                                direct_relations_statements.append(
                                    f":{instance_name} :{relation} :{entity} ."
                                )
                
                enhanced_ttl += f"                :extractedFrom \"{escape_ttl_string(result['metadata']['image_name'])}\" ;\n"
                enhanced_ttl += f"                :extractionTimestamp \"{escape_ttl_string(result['metadata']['extraction_timestamp'])}\" .\n\n"
            
            # Add directRelations, relatedTo, hasExpressor, identifiedAs, and manifestsToxicity as separate TTL statements (entity→entity relations)
            if direct_relations_statements:
                enhanced_ttl += "\n#################################################################\n"
                enhanced_ttl += "#    Direct Relations Between Entities\n"
                enhanced_ttl += "#################################################################\n\n"
                for rel_stmt in direct_relations_statements:
                    enhanced_ttl += f"{rel_stmt}\n"
                enhanced_ttl += "\n"
            
            # Generate Object Property declarations for all properties used between individuals
            object_property_declarations = self._generate_object_property_declarations(enhanced_ttl)
            if object_property_declarations:
                enhanced_ttl += "\n#################################################################\n"
                enhanced_ttl += "#    Object Property Declarations\n"
                enhanced_ttl += "#################################################################\n\n"
                enhanced_ttl += object_property_declarations
                enhanced_ttl += "\n"
            
            # Ensure we create a fresh TTL file (remove any existing file)
            if output_path.exists():
                logger.info(f"Removing existing TTL file: {output_path}")
                output_path.unlink()
            
            # Write enhanced TTL file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(enhanced_ttl)
            
            logger.info(f"Enhanced TTL file saved to: {output_path}")
            
        except Exception as e:
            logger.error(f"Failed to save enhanced TTL file: {e}")
    
    def _generate_object_property_declarations(self, ttl_content: str) -> str:
        """
        Generate Object Property declarations for properties used between individuals.
        
        This method scans the TTL content for properties used between individuals
        (e.g., :entity1 :relation :entity2) and generates Object Property declarations
        to ensure Protégé reads them correctly (instead of as Annotation Properties).
        
        Args:
            ttl_content: The TTL file content
            
        Returns:
            String containing Object Property declarations
        """
        import re
        
        # Standard RDF/OWL properties to skip (these are already declared)
        skip_properties = {
            'rdf', 'rdfs', 'owl', 'rdf_type', 'type', 
            'extractionMethod', 'extractedFrom', 'extractionTimestamp', 
            'label', 'comment', 'instance_name', 'description', 'method',
            'from', 'timestamp'
        }
        
        # Standard data properties to skip (these should remain as Annotation Properties)
        data_properties = {
            'rdfs:label', 'rdfs:comment', 'extractionMethod', 
            'extractedFrom', 'extractionTimestamp'
        }
        
        properties_used = set()
        
        # Pattern 1: Properties used between individuals at end of statement: :subject :property :object .
        # Matches: ":people :interactsWith :water ."
        property_pattern_end = r':(\w+)\s+:(\w+)\s+:(\w+)\s*\.'
        for match in re.finditer(property_pattern_end, ttl_content):
            property_name = match.group(2)
            if property_name not in skip_properties:
                properties_used.add(property_name)
        
        # Pattern 2: Properties in property lists (separated by ; or ,): :subject :property :object ;
        # Matches: ":scene :hasStaringEntity :boyfriend ;" or ":scene :features :entity ,"
        property_pattern_list = r':(\w+)\s+:(\w+)\s+:(\w+)\s*[;,]'
        for match in re.finditer(property_pattern_list, ttl_content):
            property_name = match.group(2)
            if property_name not in skip_properties:
                properties_used.add(property_name)
        
        # Pattern 3: Properties in direct relations (BackgroundKnowledge relatedTo, Scene directRelations)
        # These appear as standalone statements: ":knowledge :relatedTo :entity ."
        # Already covered by pattern 1, but let's also check for properties that might appear
        # in multi-line format
        
        # Generate Object Property declarations
        if not properties_used:
            return ""
        
        declarations = []
        for prop in sorted(properties_used):
            # Skip if it looks like a data property (contains common data property patterns)
            if prop.lower() not in ['label', 'comment', 'method', 'timestamp', 'from']:
                declarations.append(f":{prop} rdf:type owl:ObjectProperty .")
        
        return "\n".join(declarations)
    
    def _save_text_summary(self, result: Dict[str, Any], output_path: Path) -> None:
        """Save a text summary of extraction results."""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"Dimension Extraction Results\n")
            f.write(f"============================\n\n")
            
            if result["success"]:
                f.write(f"Image: {result['metadata']['image_name']}\n")
                f.write(f"Extraction Time: {result['metadata']['extraction_timestamp']}\n")
                f.write(f"LLM Provider: {result['metadata']['llm_provider']}\n")
                f.write(f"Total Dimensions Found: {result['metadata']['total_dimensions_found']}\n\n")
                
                f.write("Extracted Dimensions:\n")
                f.write("-------------------\n")
                
                for i, dim in enumerate(result["dimensions"], 1):
                    f.write(f"{i}. {dim['class_name']}: {dim['label']}\n")
                    f.write(f"   Description: {dim['description']}\n")
                    # f.write(f"   Confidence: {dim.get('confidence', 'N/A')}\n")  # Commented out - confidence field removed
                    f.write(f"   Method: {dim.get('extraction_method', 'N/A')}\n\n")
            else:
                f.write(f"Extraction failed: {result['metadata'].get('error', 'Unknown error')}\n")


# Convenience function
def extract_dimensions_from_image(
    image_path: Path,
    selected_dimensions: Optional[List[str]] = None,
    output_dir: Optional[Path] = None,
    llm_provider: str = "claude"
) -> Dict[str, Any]:
    """
    Extract dimensions from a meme image using the specialized module.
    
    Args:
        image_path: Path to the meme image
        selected_dimensions: List of dimension names to extract
        output_dir: Directory to save results
        llm_provider: LLM provider to use
        
    Returns:
        Extraction results dictionary
    """
    module = DimensionExtractionModule(llm_provider=llm_provider)
    return module.extract_dimensions_from_image(image_path, selected_dimensions, output_dir)


if __name__ == "__main__":
    # Example usage and testing
    import logging
    logging.basicConfig(level=logging.INFO)
    
    try:
        # Test with the provided meme image
        image_path = Path("/Users/stefanodegiorgis/Downloads/dev_set_task3_labeled/9_image_batch_2.png")
        
        if image_path.exists():
            # Extract dimensions
            result = extract_dimensions_from_image(
                image_path,
                selected_dimensions=["OverallIntent", "VisualMaterial", "BackgroundKnowledge"],
                output_dir=Path("output/test_extraction"),
                llm_provider="claude"
            )
            
            print(f"Extraction successful: {result['success']}")
            print(f"Dimensions found: {len(result['dimensions'])}")
            
            if result["success"]:
                for dim in result["dimensions"]:
                    print(f"- {dim['class_name']}: {dim['label']}")
        else:
            print(f"Test image not found: {image_path}")
            
    except Exception as e:
        print(f"Error: {e}")
