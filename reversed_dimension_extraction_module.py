"""
Reversed Dimension Extraction Module.

This module implements a reversed dimension extraction pipeline that starts with
OverallIntent extraction first, then extracts supporting dimensions:
TextualMaterial, VisualMaterial, Scene, and BackgroundKnowledge.
The OverallIntent graph is passed as "In context material" to all subsequent steps.

This is a parallel pipeline to the standard dimension_extraction_module.py.
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


class ReversedDimensionExtractionModule:
    """
    Reversed module for dimension extraction starting with ToxicityAssessment.
    
    This module loads prompts from JSON-LD files, starts with ToxicityAssessment
    extraction, then extracts supporting dimensions in the required order.
    """
    
    def __init__(
        self, 
        ontology_path: Optional[Path] = None,
        prompts_dir: Optional[Path] = None,
        llm_provider: str = "claude"
    ):
        """
        Initialize the reversed dimension extraction module.
        
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
        
        # Additional knowledge base (set during extraction)
        self.additional_kb_text = None
        self.iterative_kb = False
        
        logger.info(f"Reversed dimension extraction module initialized with {len(self.prompt_files)} prompt files")
    
    def _get_ordered_dimensions(self, selected_dimensions: Optional[List[str]] = None) -> List[str]:
        """
        Get dimensions in the reversed extraction order.
        
        Reversed order: OverallIntent → TextualMaterial → VisualMaterial → 
        Scene → BackgroundKnowledge → EmotionExpression → AnalogicalMapping → SemioticProjection → ToxicityAssessment → TargetCommunity
        
        Args:
            selected_dimensions: List of selected dimensions, or None for all
            
        Returns:
            List of dimensions in the reversed extraction order
        """
        # Define the reversed extraction order
        reversed_order = [
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
        
        # Get all available dimensions
        all_dimensions = list(self.prompt_files.keys())
        
        # If specific dimensions are selected, use those
        if selected_dimensions:
            # Ensure reversed order dimensions come first in order
            ordered_dimensions = []
            
            # Add reversed order dimensions in order if they're selected
            for rev_dim in reversed_order:
                if rev_dim in selected_dimensions:
                    ordered_dimensions.append(rev_dim)
            
            # Add remaining selected dimensions
            for dim in selected_dimensions:
                if dim not in ordered_dimensions:
                    ordered_dimensions.append(dim)
            
            return ordered_dimensions
        
        # If no specific dimensions, use reversed order first, then others
        else:
            # Start with reversed order
            ordered_dimensions = []
            for rev_dim in reversed_order:
                if rev_dim in all_dimensions:
                    ordered_dimensions.append(rev_dim)
            
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
    
    def _generate_incremental_ttl_graph(self, dimensions: List[Dict[str, Any]]) -> str:
        """
        Generate TTL graph incrementally from extracted dimensions.
        
        This method creates a TTL representation of the dimensions so far,
        which can be passed as "In context material" to subsequent extraction steps.
        
        Args:
            dimensions: List of extracted dimension instances
            
        Returns:
            TTL graph string representing the dimensions
        """
        if not dimensions:
            return ""
        
        ttl_graph = "\n# In Context Material - Extracted Dimensions So Far\n"
        ttl_graph += "# ====================================================\n\n"
        
        # Escape strings for TTL format
        def escape_ttl_string(text):
            if not isinstance(text, str):
                text = str(text)
            # Escape quotes and backslashes
            text = text.replace("\\", "\\\\")
            text = text.replace('"', '\\"')
            # Replace newlines with spaces
            text = text.replace('\n', ' ').replace('\r', ' ')
            # Note: No truncation - TTL format supports long strings
            return text
        
        for dim in dimensions:
            instance_name = self._normalize_instance_name(dim.get("instance_name", ""))
            class_name = dim.get("class_name", "")
            label = dim.get("label", "")
            description = dim.get("description", "")
            
            if instance_name and class_name:
                ttl_graph += f"###  http://example.org/multimodal-taxonomy#{instance_name}\n"
                ttl_graph += f":{instance_name} rdf:type :{class_name} ;\n"
                ttl_graph += f"                rdfs:label \"{escape_ttl_string(label)}\"@en ;\n"
                ttl_graph += f"                rdfs:comment \"{escape_ttl_string(description)}\"@en .\n\n"
        
        return ttl_graph
    
    def _load_additional_kb(self, kb_paths) -> Optional[str]:
        """
        Load additional knowledge base from one or more JSON-LD files.
        
        Args:
            kb_paths: Path or list of paths to JSON-LD file(s) containing additional knowledge
            
        Returns:
            Combined promptExtractionText from all JSON-LD files, or None if not found
        """
        try:
            # Handle both single path and list of paths
            if isinstance(kb_paths, Path):
                kb_paths = [kb_paths]
            elif not isinstance(kb_paths, list):
                logger.warning(f"Invalid kb_paths type: {type(kb_paths)}")
                return None
            
            all_kb_texts = []
            
            for kb_path in kb_paths:
                if not kb_path.exists():
                    logger.warning(f"Additional KB file not found: {kb_path}")
                    continue
                
                with open(kb_path, 'r', encoding='utf-8') as f:
                    kb_data = json.load(f)
                
                # Extract promptExtractionText or rdfs:comment
                kb_text = kb_data.get("promptExtractionText") or kb_data.get("rdfs:comment", "")
                
                if not kb_text:
                    logger.warning(f"No promptExtractionText or rdfs:comment found in {kb_path}")
                    continue
                
                all_kb_texts.append(kb_text)
                logger.info(f"Loaded additional KB from {kb_path.name}")
            
            if not all_kb_texts:
                return None
            
            # Combine all knowledge bases with separators
            combined_text = "\n\n".join(all_kb_texts)
            return combined_text
            
        except Exception as e:
            logger.error(f"Error loading additional KB: {e}")
            return None
    
    def extract_dimensions_from_image(
        self, 
        image_path: Path,
        selected_dimensions: Optional[List[str]] = None,
        output_dir: Optional[Path] = None,
        additional_kb_paths: Optional[List[Path]] = None,
        iterative_kb: bool = False
    ) -> Dict[str, Any]:
        """
        Extract dimensions from an image using the reversed extraction order.
        
        Starts with OverallIntent, then extracts supporting dimensions.
        The OverallIntent graph is passed as "In context material" to all subsequent steps.
        
        Args:
            image_path: Path to the meme image
            selected_dimensions: List of dimension names to extract
            output_dir: Directory to save output files
            additional_kb_paths: Optional list of paths to additional knowledge base JSON-LD files
            iterative_kb: If True, attach additional KB to all prompts; if False, only to OverallIntent
            
        Returns:
            Dictionary containing extraction results and metadata
        """
        try:
            # Validate input
            self._validate_image_path(image_path)
            
            # Load additional KB if provided
            if additional_kb_paths:
                self.additional_kb_text = self._load_additional_kb(additional_kb_paths)
                self.iterative_kb = iterative_kb
                if self.additional_kb_text:
                    logger.info(f"Additional KB loaded from {len(additional_kb_paths) if isinstance(additional_kb_paths, list) else 1} file(s). Will be included in {'all prompts' if iterative_kb else 'OverallIntent only'}")
                else:
                    logger.warning("Additional KB file(s) provided but could not be loaded")
            else:
                self.additional_kb_text = None
                self.iterative_kb = False
            
            # Determine which dimensions to extract with reversed order
            dimensions_to_extract = self._get_ordered_dimensions(selected_dimensions)
            
            logger.info(f"Extracting dimensions from: {image_path}")
            logger.info(f"Processing {len(dimensions_to_extract)} dimensions in reversed order: {dimensions_to_extract}")
            
            print(f"\n{'='*70}", flush=True)
            print(f"🚀 REVERSED PIPELINE EXTRACTION STARTED", flush=True)
            print(f"{'='*70}", flush=True)
            print(f"📁 Image: {image_path.name}", flush=True)
            print(f"📊 Pipeline Order: OverallIntent → TextualMaterial → VisualMaterial → Scene → BackgroundKnowledge → EmotionExpression → AnalogicalMapping → SemioticProjection → ToxicityAssessment → TargetCommunity", flush=True)
            print(f"🔄 Context Flow: OverallIntent graph → passed to all subsequent steps", flush=True)
            print(f"{'='*70}\n", flush=True)
            
            # Extract dimensions
            extracted_dimensions = []
            extraction_metadata = {
                "image_path": str(image_path),
                "image_name": image_path.name,
                "extraction_timestamp": datetime.now().isoformat(),
                "llm_provider": self.llm_provider,
                "dimensions_processed": [],
                "total_dimensions_found": 0,
                "pipeline_type": "reversed"
            }
            
            # Store entities for later dimensions
            visual_material_entities = []
            textual_material_entities = []
            background_knowledge_entities = []
            scene_entities = []
            emotion_expression_entities = []
            analogical_mapping_entities = []
            semiotic_projection_entities = []
            toxicity_assessment_entities = []
            overall_intent_entities = []
            overall_intent_ttl_graph = ""  # Store TTL graph from OverallIntent
            
            for dimension_name in dimensions_to_extract:
                if dimension_name not in self.prompt_files:
                    logger.warning(f"Prompt file not found for dimension: {dimension_name}")
                    continue
                
                # Print step start before LLM call
                step_num = len(extraction_metadata["dimensions_processed"]) + 1
                print(f"\n{'='*70}", flush=True)
                print(f"🔄 Step {step_num}/{len(dimensions_to_extract)}: Starting {dimension_name} extraction...", flush=True)
                print(f"{'='*70}", flush=True)
                
                try:
                    # OverallIntent is extracted first (no dependencies)
                    if dimension_name == "OverallIntent":
                        dimensions = self._extract_single_dimension(
                            image_path, 
                            dimension_name, 
                            self.prompt_files[dimension_name]
                        )
                    # For TextualMaterial, pass OverallIntent graph as context
                    elif dimension_name == "TextualMaterial":
                        dimensions = self._extract_single_dimension(
                            image_path, 
                            dimension_name, 
                            self.prompt_files[dimension_name],
                            context_ttl_graph=overall_intent_ttl_graph
                        )
                    # For VisualMaterial, pass OverallIntent graph as context
                    elif dimension_name == "VisualMaterial":
                        dimensions = self._extract_single_dimension(
                            image_path, 
                            dimension_name, 
                            self.prompt_files[dimension_name],
                            context_ttl_graph=overall_intent_ttl_graph
                        )
                    # For Scene, pass OverallIntent graph + VisualMaterial entities
                    elif dimension_name == "Scene":
                        if visual_material_entities:
                            dimensions = self._extract_single_dimension(
                                image_path, 
                                dimension_name, 
                                self.prompt_files[dimension_name],
                                visual_material_entities=visual_material_entities,
                                context_ttl_graph=overall_intent_ttl_graph
                            )
                        else:
                            logger.warning(f"Scene extraction skipped: No VisualMaterial entities available yet")
                            dimensions = []
                    # For BackgroundKnowledge, pass OverallIntent graph + VisualMaterial, TextualMaterial, and Scene entities
                    elif dimension_name == "BackgroundKnowledge":
                        dimensions = self._extract_single_dimension(
                            image_path, 
                            dimension_name, 
                            self.prompt_files[dimension_name],
                            visual_material_entities=visual_material_entities,
                            textual_material_entities=textual_material_entities,
                            scene_entities=scene_entities,
                            context_ttl_graph=overall_intent_ttl_graph
                        )
                    # For EmotionExpression, pass OverallIntent graph + VisualMaterial, TextualMaterial, Scene, BackgroundKnowledge entities
                    elif dimension_name == "EmotionExpression":
                        dimensions = self._extract_single_dimension(
                            image_path, 
                            dimension_name, 
                            self.prompt_files[dimension_name],
                            visual_material_entities=visual_material_entities,
                            textual_material_entities=textual_material_entities,
                            scene_entities=scene_entities,
                            background_knowledge_entities=background_knowledge_entities,
                            context_ttl_graph=overall_intent_ttl_graph
                        )
                    # For AnalogicalMapping, pass OverallIntent graph + VisualMaterial, TextualMaterial, Scene, BackgroundKnowledge, EmotionExpression entities
                    elif dimension_name == "AnalogicalMapping":
                        dimensions = self._extract_single_dimension(
                            image_path, 
                            dimension_name, 
                            self.prompt_files[dimension_name],
                            visual_material_entities=visual_material_entities,
                            textual_material_entities=textual_material_entities,
                            scene_entities=scene_entities,
                            background_knowledge_entities=background_knowledge_entities,
                            emotion_expression_entities=emotion_expression_entities,
                            context_ttl_graph=overall_intent_ttl_graph
                        )
                    # For SemioticProjection, pass OverallIntent graph + VisualMaterial, TextualMaterial, Scene, BackgroundKnowledge, AnalogicalMapping entities
                    elif dimension_name == "SemioticProjection":
                        dimensions = self._extract_single_dimension(
                            image_path, 
                            dimension_name, 
                            self.prompt_files[dimension_name],
                            visual_material_entities=visual_material_entities,
                            textual_material_entities=textual_material_entities,
                            scene_entities=scene_entities,
                            background_knowledge_entities=background_knowledge_entities,
                            analogical_mapping_entities=analogical_mapping_entities,
                            context_ttl_graph=overall_intent_ttl_graph
                        )
                    # For ToxicityAssessment, pass OverallIntent graph + VisualMaterial, TextualMaterial, Scene, BackgroundKnowledge, EmotionExpression, AnalogicalMapping, SemioticProjection entities
                    elif dimension_name == "ToxicityAssessment":
                        dimensions = self._extract_single_dimension(
                            image_path, 
                            dimension_name, 
                            self.prompt_files[dimension_name],
                            visual_material_entities=visual_material_entities,
                            textual_material_entities=textual_material_entities,
                            scene_entities=scene_entities,
                            background_knowledge_entities=background_knowledge_entities,
                            emotion_expression_entities=emotion_expression_entities,
                            analogical_mapping_entities=analogical_mapping_entities,
                            semiotic_projection_entities=semiotic_projection_entities,
                            context_ttl_graph=overall_intent_ttl_graph
                        )
                    # For TargetCommunity, pass OverallIntent graph + VisualMaterial, TextualMaterial, Scene, BackgroundKnowledge, AnalogicalMapping, ToxicityAssessment entities
                    elif dimension_name == "TargetCommunity":
                        dimensions = self._extract_single_dimension(
                            image_path, 
                            dimension_name, 
                            self.prompt_files[dimension_name],
                            visual_material_entities=visual_material_entities,
                            textual_material_entities=textual_material_entities,
                            scene_entities=scene_entities,
                            background_knowledge_entities=background_knowledge_entities,
                            analogical_mapping_entities=analogical_mapping_entities,
                            toxicity_assessment_entities=toxicity_assessment_entities,
                            context_ttl_graph=overall_intent_ttl_graph
                        )
                    else:
                        # For other dimensions - extract with image only
                        dimensions = self._extract_single_dimension(
                            image_path, 
                            dimension_name, 
                            self.prompt_files[dimension_name]
                        )
                    
                    # Handle results (even if empty)
                    if dimensions is not None:
                        # CRITICAL: Normalize all dimension instances BEFORE storing/passing to other phases
                        if dimensions:
                            for dim in dimensions:
                                if isinstance(dim, dict):
                                    # Normalize the main instance_name
                                    if "instance_name" in dim:
                                        original_name = dim["instance_name"]
                                        dim["instance_name"] = self._normalize_instance_name(original_name)
                                        if original_name != dim["instance_name"]:
                                            logger.debug(f"Normalized instance_name: '{original_name}' -> '{dim['instance_name']}'")
                                    
                                    # Normalize entity references in relations
                                    self._normalize_entity_references(dim)
                        
                        if dimensions:  # Non-empty list
                            extracted_dimensions.extend(dimensions)
                            extraction_metadata["dimensions_processed"].append(dimension_name)
                            logger.info(f"Extracted {len(dimensions)} instances for dimension: {dimension_name}")
                            
                            # Print step information
                            step_num = len(extraction_metadata["dimensions_processed"])
                            print(f"\n{'='*70}", flush=True)
                            print(f"✅ Step {step_num}/{len(dimensions_to_extract)}: {dimension_name} - COMPLETED", flush=True)
                            print(f"{'='*70}", flush=True)
                            print(f"   Extracted {len(dimensions)} instance(s)", flush=True)
                            
                            # Show context being passed to next steps
                            if dimension_name == "OverallIntent":
                                print(f"   📊 Generated TTL graph from OverallIntent ({len(dimensions)} entities)", flush=True)
                                print(f"   ➡️  This graph will be passed as 'In context material' to all subsequent steps", flush=True)
                            elif dimension_name == "TextualMaterial":
                                print(f"   📥 Received OverallIntent graph as context", flush=True)
                            elif dimension_name == "VisualMaterial":
                                print(f"   📥 Received OverallIntent graph as context", flush=True)
                            elif dimension_name == "Scene":
                                print(f"   📥 Received OverallIntent graph + {len(visual_material_entities)} VisualMaterial entities", flush=True)
                            elif dimension_name == "BackgroundKnowledge":
                                print(f"   📥 Received OverallIntent graph + {len(visual_material_entities)} VisualMaterial + {len(textual_material_entities)} TextualMaterial + {len(scene_entities)} Scene entities", flush=True)
                            elif dimension_name == "EmotionExpression":
                                print(f"   📥 Received OverallIntent graph + {len(visual_material_entities)} VisualMaterial + {len(textual_material_entities)} TextualMaterial + {len(scene_entities)} Scene + {len(background_knowledge_entities)} BackgroundKnowledge entities", flush=True)
                            elif dimension_name == "AnalogicalMapping":
                                print(f"   📥 Received OverallIntent graph + {len(visual_material_entities)} VisualMaterial + {len(textual_material_entities)} TextualMaterial + {len(scene_entities)} Scene + {len(background_knowledge_entities)} BackgroundKnowledge + {len(emotion_expression_entities)} EmotionExpression entities", flush=True)
                            elif dimension_name == "SemioticProjection":
                                print(f"   📥 Received OverallIntent graph + {len(visual_material_entities)} VisualMaterial + {len(textual_material_entities)} TextualMaterial + {len(scene_entities)} Scene + {len(background_knowledge_entities)} BackgroundKnowledge + {len(analogical_mapping_entities)} AnalogicalMapping entities", flush=True)
                            elif dimension_name == "ToxicityAssessment":
                                print(f"   📥 Received OverallIntent graph + {len(visual_material_entities)} VisualMaterial + {len(textual_material_entities)} TextualMaterial + {len(scene_entities)} Scene + {len(background_knowledge_entities)} BackgroundKnowledge + {len(emotion_expression_entities)} EmotionExpression + {len(analogical_mapping_entities)} AnalogicalMapping + {len(semiotic_projection_entities)} SemioticProjection entities", flush=True)
                            elif dimension_name == "TargetCommunity":
                                print(f"   📥 Received OverallIntent graph + {len(visual_material_entities)} VisualMaterial + {len(textual_material_entities)} TextualMaterial + {len(scene_entities)} Scene + {len(background_knowledge_entities)} BackgroundKnowledge + {len(analogical_mapping_entities)} AnalogicalMapping + {len(toxicity_assessment_entities)} ToxicityAssessment entities", flush=True)
                            
                            # Print terminal output for key dimensions
                            if dimension_name in ["OverallIntent", "TextualMaterial", "VisualMaterial", "BackgroundKnowledge", "Scene", "EmotionExpression", "AnalogicalMapping", "SemioticProjection", "ToxicityAssessment", "TargetCommunity"]:
                                self._print_dimension_output(dimension_name, dimensions)
                        else:  # Empty list
                            logger.warning(f"Extracted 0 instances for dimension: {dimension_name} (empty result)")
                            extraction_metadata["dimensions_processed"].append(dimension_name)
                        
                        # Store OverallIntent graph after extraction
                        if dimension_name == "OverallIntent" and dimensions:
                            overall_intent_entities = dimensions
                            # Generate TTL graph from OverallIntent
                            overall_intent_ttl_graph = self._generate_incremental_ttl_graph(overall_intent_entities)
                            logger.info(f"Stored {len(overall_intent_entities)} OverallIntent entities and generated context graph")
                            print(f"   📝 OverallIntent TTL graph generated ({len(overall_intent_ttl_graph)} characters)", flush=True)
                        
                        # Store entities for later dimensions
                        if dimension_name == "VisualMaterial" and dimensions:
                            visual_material_entities = dimensions
                            logger.info(f"Stored {len(visual_material_entities)} VisualMaterial entities")
                        
                        if dimension_name == "TextualMaterial" and dimensions:
                            textual_material_entities = dimensions
                            logger.info(f"Stored {len(textual_material_entities)} TextualMaterial entities")
                        
                        if dimension_name == "Scene" and dimensions:
                            scene_entities = dimensions
                            logger.info(f"Stored {len(scene_entities)} Scene entities")
                        
                        if dimension_name == "BackgroundKnowledge" and dimensions:
                            background_knowledge_entities = dimensions
                            logger.info(f"Stored {len(background_knowledge_entities)} BackgroundKnowledge entities")
                        
                        if dimension_name == "EmotionExpression" and dimensions:
                            emotion_expression_entities = dimensions
                            logger.info(f"Stored {len(emotion_expression_entities)} EmotionExpression entities")
                        
                        if dimension_name == "AnalogicalMapping" and dimensions:
                            analogical_mapping_entities = dimensions
                            logger.info(f"Stored {len(analogical_mapping_entities)} AnalogicalMapping entities")
                        
                        if dimension_name == "SemioticProjection" and dimensions:
                            semiotic_projection_entities = dimensions
                            logger.info(f"Stored {len(semiotic_projection_entities)} SemioticProjection entities")
                        
                        if dimension_name == "ToxicityAssessment" and dimensions:
                            toxicity_assessment_entities = dimensions
                            logger.info(f"Stored {len(toxicity_assessment_entities)} ToxicityAssessment entities")
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
            
            # Print final summary
            print(f"\n{'='*70}", flush=True)
            print(f"✅ REVERSED PIPELINE EXTRACTION COMPLETED", flush=True)
            print(f"{'='*70}", flush=True)
            print(f"📊 Total dimensions extracted: {len(extracted_dimensions)}", flush=True)
            print(f"🔍 Dimensions processed: {', '.join(extraction_metadata['dimensions_processed'])}", flush=True)
            if output_dir:
                print(f"📁 Output directory: {output_dir}", flush=True)
            print(f"{'='*70}\n", flush=True)
            
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
        scene_entities: Optional[List[Dict[str, Any]]] = None,
        emotion_expression_entities: Optional[List[Dict[str, Any]]] = None,
        analogical_mapping_entities: Optional[List[Dict[str, Any]]] = None,
        semiotic_projection_entities: Optional[List[Dict[str, Any]]] = None,
        toxicity_assessment_entities: Optional[List[Dict[str, Any]]] = None,
        context_ttl_graph: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Extract instances for a single dimension using its prompt file.
        
        Args:
            image_path: Path to the image
            dimension_name: Name of the dimension
            prompt_data: Prompt data from JSON-LD file
            visual_material_entities: Optional list of VisualMaterial entities
            textual_material_entities: Optional list of TextualMaterial entities
            background_knowledge_entities: Optional list of BackgroundKnowledge entities
            scene_entities: Optional list of Scene entities
            context_ttl_graph: Optional TTL graph string from previous extractions
            
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
            scene_entities=scene_entities,
            emotion_expression_entities=emotion_expression_entities,
            analogical_mapping_entities=analogical_mapping_entities,
            semiotic_projection_entities=semiotic_projection_entities,
            toxicity_assessment_entities=toxicity_assessment_entities,
            context_ttl_graph=context_ttl_graph
        )
        
        # Generate response using LLM
        try:
            logger.info(f"Generating response for {dimension_name} using provider: {self.llm_provider}")
            logger.info(f"Model being used: {self.llm_manager.get_current_model()}")
            
            # Check if provider is available
            available_providers = self.llm_manager.get_available_providers()
            logger.info(f"Available providers: {available_providers}")
            
            if self.llm_provider not in available_providers:
                error_msg = f"Provider '{self.llm_provider}' not available. Available providers: {available_providers}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            logger.info(f"Calling LLM for {dimension_name}...")
            print(f"   🤖 Making LLM API call to {self.llm_provider}...", flush=True)
            response = self.llm_manager.generate_response(
                full_prompt, 
                image_path, 
                provider=self.llm_provider
            )
            print(f"   ✅ LLM response received ({len(response)} characters)", flush=True)
            
            if not response or not response.strip():
                logger.error(f"Empty or None response received for {dimension_name}")
                return []
            
            logger.info(f"Received response for {dimension_name} (length: {len(response)} chars)")
            logger.debug(f"Response preview (first 500 chars): {response[:500]}")
            
            # Parse the response
            dimensions = self._parse_extraction_response(response, dimension_name, prompt_data)
            logger.info(f"Parsed {len(dimensions)} dimensions from response for {dimension_name}")
            
            if len(dimensions) == 0:
                logger.warning(f"⚠️  WARNING: Zero dimensions extracted for {dimension_name}!")
                logger.warning(f"Full response (first 2000 chars): {response[:2000]}")
            
            return dimensions
            
        except Exception as e:
            logger.error(f"LLM extraction failed for dimension {dimension_name}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def _create_extraction_prompt(
        self, 
        base_prompt: str, 
        prompt_data: Dict[str, Any],
        dimension_name: str,
        visual_material_entities: Optional[List[Dict[str, Any]]] = None,
        textual_material_entities: Optional[List[Dict[str, Any]]] = None,
        background_knowledge_entities: Optional[List[Dict[str, Any]]] = None,
        scene_entities: Optional[List[Dict[str, Any]]] = None,
        emotion_expression_entities: Optional[List[Dict[str, Any]]] = None,
        analogical_mapping_entities: Optional[List[Dict[str, Any]]] = None,
        semiotic_projection_entities: Optional[List[Dict[str, Any]]] = None,
        toxicity_assessment_entities: Optional[List[Dict[str, Any]]] = None,
        context_ttl_graph: Optional[str] = None
    ) -> str:
        """
        Create the full extraction prompt for a dimension.
        
        Args:
            base_prompt: Base prompt from JSON-LD file
            prompt_data: Complete prompt data
            dimension_name: Name of the dimension being extracted
            visual_material_entities: Optional list of VisualMaterial entities
            textual_material_entities: Optional list of TextualMaterial entities
            background_knowledge_entities: Optional list of BackgroundKnowledge entities
            scene_entities: Optional list of Scene entities
            analogical_mapping_entities: Optional list of AnalogicalMapping entities
            context_ttl_graph: Optional TTL graph string from previous extractions (OverallIntent)
            
        Returns:
            Complete extraction prompt
        """
        # Add dimension context
        dimension_label = prompt_data.get("rdfs:label", "Unknown Dimension")
        dimension_comment = prompt_data.get("rdfs:comment", "")
        
        # Build "In context material" section if TTL graph is provided
        context_section = ""
        if context_ttl_graph:
            context_section = f"""
========================================
In Context Material for the Meme Analysis
========================================

The following knowledge graph represents dimensions extracted in previous steps. Use this context to guide your extraction:

{context_ttl_graph}

========================================
"""
        
        # Add additional KB section if applicable
        additional_kb_section = ""
        if self.additional_kb_text and (dimension_name == "OverallIntent" or self.iterative_kb):
            additional_kb_section = f"""

For this specific task keep in mind this further additional knowledge:

{self.additional_kb_text}

"""
        
        # For OverallIntent (first extraction), no dependencies
        if dimension_name == "OverallIntent":
            full_prompt = f"""You are analyzing a meme image to extract {dimension_label} dimensions.

Dimension: {dimension_label}
Description: {dimension_comment}
{additional_kb_section}
{base_prompt}

Please analyze the image and provide your response in the exact JSON format specified in the prompt above. Be thorough and accurate in your analysis."""
        
        # For TextualMaterial, pass OverallIntent graph as context
        elif dimension_name == "TextualMaterial":
            full_prompt = f"""You are analyzing a meme image to extract {dimension_label} dimensions.

Dimension: {dimension_label}
Description: {dimension_comment}
{context_section}
{additional_kb_section}
{base_prompt}

Please analyze the image and provide your response in the exact JSON format specified in the prompt above. Be thorough and accurate in your analysis."""
        
        # For VisualMaterial, pass OverallIntent graph as context
        elif dimension_name == "VisualMaterial":
            full_prompt = f"""You are analyzing a meme image to extract {dimension_label} dimensions.

Dimension: {dimension_label}
Description: {dimension_comment}
{context_section}
{additional_kb_section}
{base_prompt}

Please analyze the image and provide your response in the exact JSON format specified in the prompt above. Be thorough and accurate in your analysis."""
        
        # For Scene, pass OverallIntent graph + VisualMaterial entities
        elif dimension_name == "Scene":
            entities_context = "\n\nVisual Material entities found in the image (use only these entity names exactly as shown):\n"
            for i, entity in enumerate(visual_material_entities or [], 1):
                instance_name = entity.get("instance_name", f"entity_{i}")
                label = entity.get("label", "unknown entity")
                description = entity.get("description", "")
                entities_context += f"- {instance_name}: {label} ({description})\n"
            
            full_prompt = f"""You are analyzing a meme image to extract {dimension_label} dimensions.

Dimension: {dimension_label}
Description: {dimension_comment}
{context_section}
{additional_kb_section}
{entities_context}

{base_prompt}

IMPORTANT: 
- If you need, these individuals are already present in the graphs. Use them as anchoring points to attach any new individuals you generate.
- Use only the VisualMaterial entity names provided above (e.g., use "people", "water", "text" exactly as shown).
- You MUST return at least one scene showing how these entities relate to each other.
- Each scene should have hasEntities and directRelations.
- Do not return an empty array. Always create at least one scene.

Please analyze the image and provide your response in the exact JSON format specified in the prompt above. Be thorough and accurate in your analysis."""
        
        # For BackgroundKnowledge, pass OverallIntent graph + VisualMaterial, TextualMaterial, and Scene entities
        elif dimension_name == "BackgroundKnowledge":
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
            
            if scene_entities:
                entities_context += "\nScene entities:\n"
                for i, entity in enumerate(scene_entities, 1):
                    instance_name = entity.get("instance_name", f"entity_{i}")
                    label = entity.get("label", "unknown entity")
                    description = entity.get("description", "")
                    entities_context += f"- {instance_name}: {label} ({description})\n"
            
            full_prompt = f"""You are analyzing a meme image to extract {dimension_label} dimensions.

Dimension: {dimension_label}
Description: {dimension_comment}
{context_section}
{additional_kb_section}
IMPORTANT: Background Knowledge refers to pieces of knowledge OUTSIDE the image that are needed to understand the meme. These are real-world entities, events, concepts, or references that are implicitly referred to but NOT directly visible in the image. Examples:
- Actor/character names (if a person in the image resembles a known actor)
- Historical events (if the scene references a historical event)
- Countries, political parties, art movements
- Cultural phenomena, social trends, or any real-world knowledge implicitly referenced

{entities_context}

{base_prompt}

IMPORTANT: 
- If you need, these individuals are already present in the graphs. Use them as anchoring points to attach any new individuals you generate.
- Focus ONLY on knowledge OUTSIDE the image, NOT what is directly visible.
- Use only the entity names provided above (e.g., use "people", "water", "text_chunk" exactly as shown).
- For each BackgroundKnowledge item, add relatedTo linking to VisualMaterial, TextualMaterial, or Scene entities that require this external knowledge to be understood.
- You MUST include relatedTo relations for at least some BackgroundKnowledge items.

Please analyze the image and provide your response in the exact JSON format specified in the prompt above. Be thorough and accurate in your analysis."""
        
        # For EmotionExpression, pass OverallIntent graph + VisualMaterial, TextualMaterial, Scene, BackgroundKnowledge entities
        elif dimension_name == "EmotionExpression":
            entities_context = "\n\nEntities found in the image (use these to identify emotion expressions):\n"
            
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
            
            if scene_entities:
                entities_context += "\nScene entities:\n"
                for i, entity in enumerate(scene_entities, 1):
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
            
            full_prompt = f"""You are analyzing a meme image to extract {dimension_label} dimensions.

Dimension: {dimension_label}
Description: {dimension_comment}
{context_section}
{additional_kb_section}
{entities_context}

{base_prompt}

IMPORTANT: 
- If you need, these individuals are already present in the graphs. Use them as anchoring points to attach any new individuals you generate.
- Use only the entity names provided above (e.g., use "person", "text_chunk", "scene_1" exactly as shown).

Please analyze the image and provide your response in the exact JSON format specified in the prompt above. Be thorough and accurate in your analysis."""
        
        # For AnalogicalMapping, pass OverallIntent graph + VisualMaterial, TextualMaterial, Scene, BackgroundKnowledge, EmotionExpression entities
        elif dimension_name == "AnalogicalMapping":
            entities_context = "\n\nEntities found in the image (use these to identify analogical mappings):\n"
            
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
            
            if scene_entities:
                entities_context += "\nScene entities:\n"
                for i, entity in enumerate(scene_entities, 1):
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
            
            if emotion_expression_entities:
                entities_context += "\nEmotion Expression entities:\n"
                for i, entity in enumerate(emotion_expression_entities, 1):
                    instance_name = entity.get("instance_name", f"entity_{i}")
                    label = entity.get("label", "unknown entity")
                    description = entity.get("description", "")
                    entities_context += f"- {instance_name}: {label} ({description})\n"
            
            full_prompt = f"""You are analyzing a meme image to extract {dimension_label} dimensions.

Dimension: {dimension_label}
Description: {dimension_comment}
{context_section}
{additional_kb_section}
{entities_context}

{base_prompt}

IMPORTANT: 
- If you need, these individuals are already present in the graphs. Use them as anchoring points to attach any new individuals you generate.
- Identify analogical mappings between textual material and visual material.
- The task is to identify when a textual element (e.g., "me", or some other entity referred to in the textual material) is projected onto a visual element.
- This can happen through spatial adjacency, text positioning, or other contextual cues.
- For each mapping found, create relations as specified in the prompt (hasMappedEntity, hasMappingEntity, etc.).
- Use only the entity names provided above (e.g., use "person", "text_chunk", "me" exactly as shown).
- Focus on clear cases where text explicitly or implicitly identifies something as something else in the visual material.

Please analyze the image and provide your response in the exact JSON format specified in the prompt above. Be thorough and accurate in your analysis."""
        
        # For SemioticProjection, pass OverallIntent graph + VisualMaterial, TextualMaterial, Scene, BackgroundKnowledge, AnalogicalMapping entities
        elif dimension_name == "SemioticProjection":
            entities_context = "\n\nEntities found in the image (use these to identify semiotic projections):\n"
            
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
            
            if scene_entities:
                entities_context += "\nScene entities:\n"
                for i, entity in enumerate(scene_entities, 1):
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
            
            if analogical_mapping_entities:
                entities_context += "\nAnalogical Mapping entities:\n"
                for i, entity in enumerate(analogical_mapping_entities, 1):
                    instance_name = entity.get("instance_name", f"entity_{i}")
                    label = entity.get("label", "unknown entity")
                    description = entity.get("description", "")
                    entities_context += f"- {instance_name}: {label} ({description})\n"
            
            full_prompt = f"""You are analyzing a meme image to extract {dimension_label} dimensions.

Dimension: {dimension_label}
Description: {dimension_comment}
{context_section}
{additional_kb_section}
{entities_context}

{base_prompt}

IMPORTANT:
- If you need, these individuals are already present in the graphs. Use them as anchoring points to attach any new individuals you generate.
- Identify if the User is projected onto some element of the meme (e.g., explicit deictics like "me", "you", "your...", "mine..." etc.).
- Use only the entity names provided above (e.g., use "person", "text_chunk", "scene_1" exactly as shown).
- Create semiotic projection nodes with hasProjectedUser and hasProjectedEntity relations as specified in the prompt.

Please analyze the image and provide your response in the exact JSON format specified in the prompt above. Be thorough and accurate in your analysis."""
        
        # For ToxicityAssessment, pass OverallIntent graph + VisualMaterial, TextualMaterial, Scene, BackgroundKnowledge, EmotionExpression, AnalogicalMapping, SemioticProjection entities
        elif dimension_name == "ToxicityAssessment":
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
            
            if scene_entities:
                entities_context += "\nScene entities:\n"
                for i, entity in enumerate(scene_entities, 1):
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
            
            if emotion_expression_entities:
                entities_context += "\nEmotion Expression entities:\n"
                for i, entity in enumerate(emotion_expression_entities, 1):
                    instance_name = entity.get("instance_name", f"entity_{i}")
                    label = entity.get("label", "unknown entity")
                    description = entity.get("description", "")
                    entities_context += f"- {instance_name}: {label} ({description})\n"
            
            if analogical_mapping_entities:
                entities_context += "\nAnalogical Mapping entities:\n"
                for i, entity in enumerate(analogical_mapping_entities, 1):
                    instance_name = entity.get("instance_name", f"entity_{i}")
                    label = entity.get("label", "unknown entity")
                    description = entity.get("description", "")
                    entities_context += f"- {instance_name}: {label} ({description})\n"
            
            if semiotic_projection_entities:
                entities_context += "\nSemiotic Projection entities:\n"
                for i, entity in enumerate(semiotic_projection_entities, 1):
                    instance_name = entity.get("instance_name", f"entity_{i}")
                    label = entity.get("label", "unknown entity")
                    description = entity.get("description", "")
                    entities_context += f"- {instance_name}: {label} ({description})\n"
            
            full_prompt = f"""You are analyzing a meme image to extract {dimension_label} dimensions.

Dimension: {dimension_label}
Description: {dimension_comment}
{context_section}
{additional_kb_section}
{entities_context}

{base_prompt}

IMPORTANT:
- If you need, these individuals are already present in the graphs. Use them as anchoring points to attach any new individuals you generate. 
- Assess toxicity for entities from VisualMaterial, TextualMaterial, Scene, BackgroundKnowledge, AnalogicalMapping, and SemioticProjection.
- Use only the entity names provided above (e.g., use "person", "text_chunk", "mapping" exactly as shown).
- For each entity that manifests toxicity, create a manifestsToxicity relation linking the entity to the toxicity type.
- If an entity manifests multiple types of toxicity, include all of them.
- If no toxicity is found, return an empty array.

Please analyze the image and provide your response in the exact JSON format specified in the prompt above. Be thorough and accurate in your analysis."""
        
        # For TargetCommunity, pass OverallIntent graph + VisualMaterial, TextualMaterial, Scene, BackgroundKnowledge, AnalogicalMapping, ToxicityAssessment entities
        elif dimension_name == "TargetCommunity":
            entities_context = "\n\nEntities found in the image (use these to identify target community):\n"
            
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
            
            if scene_entities:
                entities_context += "\nScene entities:\n"
                for i, entity in enumerate(scene_entities, 1):
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
            
            if analogical_mapping_entities:
                entities_context += "\nAnalogical Mapping entities:\n"
                for i, entity in enumerate(analogical_mapping_entities, 1):
                    instance_name = entity.get("instance_name", f"entity_{i}")
                    label = entity.get("label", "unknown entity")
                    description = entity.get("description", "")
                    entities_context += f"- {instance_name}: {label} ({description})\n"
            
            if toxicity_assessment_entities:
                entities_context += "\nToxicity Assessment entities:\n"
                for i, entity in enumerate(toxicity_assessment_entities, 1):
                    instance_name = entity.get("instance_name", f"entity_{i}")
                    label = entity.get("label", "unknown entity")
                    description = entity.get("description", "")
                    entities_context += f"- {instance_name}: {label} ({description})\n"
            
            full_prompt = f"""You are analyzing a meme image to extract {dimension_label} dimensions.

Dimension: {dimension_label}
Description: {dimension_comment}
{context_section}
{additional_kb_section}
{entities_context}

{base_prompt}

IMPORTANT:
- If you need, these individuals are already present in the graphs. Use them as anchoring points to attach any new individuals you generate.
- Identify the intended audience or community for which the meme is designed.
- Use only the entity names provided above (e.g., use "person", "text_chunk", "scene_1" exactly as shown).
- Consider demographic cues, cultural references, and community-specific elements.

Please analyze the image and provide your response in the exact JSON format specified in the prompt above. Be thorough and accurate in your analysis."""
        else:
            # For other dimensions - create the full prompt with context if available
            full_prompt = f"""You are analyzing a meme image to extract {dimension_label} dimensions.

Dimension: {dimension_label}
Description: {dimension_comment}
{context_section}
{additional_kb_section}
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
            logger.debug(f"Extracted JSON data type: {type(json_data)}, value: {json_data}")
            
            if json_data is None:
                logger.warning(f"No JSON data extracted from response for {dimension_name}")
                logger.warning(f"Response content (first 1000 chars): {response[:1000]}")
                # Try to extract dimensions using regex as fallback
                dimensions = self._extract_dimensions_with_regex(response, dimension_name, prompt_data)
                return dimensions
            
            if isinstance(json_data, list):
                logger.debug(f"Processing {len(json_data)} items from list for {dimension_name}")
                # Multiple dimensions
                for i, item in enumerate(json_data):
                    try:
                        # Normalize entity references BEFORE creating dimension instance
                        item = self._normalize_entity_references(item)
                        dimension_instances = self._create_dimension_instance(item, dimension_name, prompt_data)
                        if dimension_instances:
                            if isinstance(dimension_instances, list):
                                dimensions.extend(dimension_instances)
                                logger.debug(f"Added {len(dimension_instances)} instances from item {i}")
                            else:
                                dimensions.append(dimension_instances)
                                logger.debug(f"Added 1 instance from item {i}")
                        else:
                            logger.warning(f"_create_dimension_instance returned None/empty for item {i} in {dimension_name}")
                    except Exception as e:
                        logger.error(f"Error processing item {i} for {dimension_name}: {e}")
                        import traceback
                        logger.error(traceback.format_exc())
            elif isinstance(json_data, dict):
                logger.debug(f"Processing single dict for {dimension_name}")
                # Single dimension
                # Normalize entity references BEFORE creating dimension instance
                json_data = self._normalize_entity_references(json_data)
                dimension_instances = self._create_dimension_instance(json_data, dimension_name, prompt_data)
                if dimension_instances:
                    if isinstance(dimension_instances, list):
                        dimensions.extend(dimension_instances)
                        logger.debug(f"Added {len(dimension_instances)} instances from dict")
                    else:
                        dimensions.append(dimension_instances)
                        logger.debug(f"Added 1 instance from dict")
                else:
                    logger.warning(f"_create_dimension_instance returned None/empty for dict in {dimension_name}")
                    logger.warning(f"JSON data was: {json_data}")
            else:
                logger.warning(f"Extracted JSON data is not a list or dict for {dimension_name}. Type: {type(json_data)}, Value: {json_data}")
                logger.warning(f"Response content (first 1000 chars): {response[:1000]}")
                # Try to extract dimensions using regex as fallback
                dimensions = self._extract_dimensions_with_regex(response, dimension_name, prompt_data)
            
        except ValueError as e:
            # This is raised by _extract_json_from_response when no JSON is found
            logger.warning(f"No valid JSON found in response for dimension {dimension_name}: {e}")
            logger.warning(f"Response content (first 1000 chars): {response[:1000]}")
            # Try to extract dimensions using regex as fallback
            dimensions = self._extract_dimensions_with_regex(response, dimension_name, prompt_data)
        except Exception as e:
            logger.error(f"Failed to parse response for dimension {dimension_name}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            logger.warning(f"Response content (first 1000 chars): {response[:1000]}")
            # Try to extract dimensions using regex as fallback
            dimensions = self._extract_dimensions_with_regex(response, dimension_name, prompt_data)
        
        return dimensions
    
    def _extract_json_from_response(self, response: str) -> Any:
        """Extract JSON data from LLM response with enhanced parsing."""
        import re
        
        # Enhanced patterns for LLM responses
        json_patterns = [
            r'```json\s*(.*?)\s*```',
            r'```\s*(.*?)\s*```',
            r'\{[^{}]*"instance_name"[^{}]*\}',
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
        Normalize all entity references in dimension data.
        
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
            
            # Universal dimension instance creation
            if "instance_name" in data and "label" in data:
                # Use provided description or build from other fields
                if "description" in data:
                    description = data["description"]
                else:
                    # Build description from available fields
                    description_parts = []
                    for key, value in data.items():
                        if key not in ['instance_name', 'label', 'confidence', '@context', '@type', '@id', 'hasEntities', 'directRelations', 'relatedTo', 'identifiedAs', 'manifestsToxicity']:
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
                    "extraction_method": f"llm_extraction_{self.llm_provider}",
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
                                        "extraction_method": f"llm_extraction_{self.llm_provider}",
                                        "dimension_index": prompt_data.get("dimensionIndex", 0)
                                    }
                                    formatted_instances.append(dimension)
            
            # Strategy 3: Single object with custom fields
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
                    "extraction_method": f"llm_extraction_{self.llm_provider}",
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
                
                # For AnalogicalMapping, preserve identifiedAs relations
                if dimension_name == "AnalogicalMapping":
                    if "identifiedAs" in data:
                        dimension["identifiedAs"] = data["identifiedAs"]
                
                # For ToxicityAssessment, preserve manifestsToxicity relations
                if dimension_name == "ToxicityAssessment":
                    if "manifestsToxicity" in data:
                        dimension["manifestsToxicity"] = data["manifestsToxicity"]
                
                formatted_instances.append(dimension)
            
            return formatted_instances if formatted_instances else None
            
        except Exception as e:
            logger.error(f"Error creating dimension instance: {e}")
            return None
    
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
            dimension_name: Name of the dimension
            dimensions: List of extracted dimension instances
        """
        print(f"\n{'='*70}", flush=True)
        print(f"📋 {dimension_name} Entities ({len(dimensions)} found)", flush=True)
        print(f"{'='*70}", flush=True)
        
        for i, dim in enumerate(dimensions, 1):
            instance_name = dim.get("instance_name", "unknown")
            label = dim.get("label", "N/A")
            description = dim.get("description", "N/A")
            
            print(f"\n  {i}. {instance_name}", flush=True)
            print(f"     Label: {label}", flush=True)
            if description and description != label:
                # Truncate long descriptions
                desc = description[:200] + "..." if len(description) > 200 else description
                print(f"     Description: {desc}", flush=True)
            
            # Special handling for Scene with frame-based relations
            if dimension_name == "Scene":
                if "hasEntities" in dim and dim["hasEntities"]:
                    print(f"     Scene → Entity Relations:", flush=True)
                    for rel in dim["hasEntities"]:
                        relation = rel.get("relation", "unknown")
                        entity = rel.get("entity", "unknown")
                        print(f"       • {relation}: {entity}", flush=True)
                
                if "directRelations" in dim and dim["directRelations"]:
                    print(f"     Entity → Entity Relations:", flush=True)
                    for rel in dim["directRelations"]:
                        from_entity = rel.get("from", "unknown")
                        relation = rel.get("relation", "unknown")
                        to_entity = rel.get("to", "unknown")
                        print(f"       • {from_entity} {relation} {to_entity}", flush=True)
            
            # Special handling for BackgroundKnowledge with relatedTo relations
            if dimension_name == "BackgroundKnowledge":
                if "relatedTo" in dim and dim["relatedTo"]:
                    print(f"     BackgroundKnowledge → Entity Relations:", flush=True)
                    for rel in dim["relatedTo"]:
                        relation = rel.get("relation", "relatedTo")
                        entity = rel.get("entity", "unknown")
                        print(f"       • {relation}: {entity}", flush=True)
            
            # Special handling for ToxicityAssessment with manifestsToxicity relations
            if dimension_name == "ToxicityAssessment":
                if "manifestsToxicity" in dim and dim["manifestsToxicity"]:
                    print(f"     ToxicityAssessment → Toxicity Type Relations:")
                    for rel in dim["manifestsToxicity"]:
                        relation = rel.get("relation", "manifestsToxicity")
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
                
                jsonld_path = output_dir / f"{base_name}_dimensions_reversed.jsonld"
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
                raw_json_path = output_dir / f"{base_name}_dimensions_reversed_raw.json"
                with open(raw_json_path, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)
                saved_files["raw_json"] = raw_json_path
            
            # Save enhanced TTL file
            ttl_path = output_dir / f"{base_name}_enhanced_ontology_reversed.ttl"
            self._save_enhanced_ttl(result, ttl_path)
            saved_files["enhanced_ttl"] = ttl_path
            
            # Save text summary
            text_path = output_dir / f"{base_name}_dimensions_reversed.txt"
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
            enhanced_ttl += "#    Extracted Dimension Instances (Reversed Pipeline)\n"
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
                    # Note: No truncation - TTL format supports long strings with proper escaping
                    return text
                
                enhanced_ttl += f"###  http://example.org/multimodal-taxonomy#{instance_name}\n"
                enhanced_ttl += f":{instance_name} rdf:type :{class_name} ;\n"
                enhanced_ttl += f"                rdfs:label \"{escape_ttl_string(dim['label'])}\"@en ;\n"
                enhanced_ttl += f"                rdfs:comment \"{escape_ttl_string(dim['description'])}\"@en ;\n"
                enhanced_ttl += f"                :extractionMethod \"{escape_ttl_string(dim['extraction_method'])}\" ;\n"
                
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
            
            # Add directRelations, relatedTo, identifiedAs, and manifestsToxicity as separate TTL statements (entity→entity relations)
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
            f.write(f"Reversed Dimension Extraction Results\n")
            f.write(f"=====================================\n\n")
            
            if result["success"]:
                f.write(f"Pipeline Type: Reversed (starts with ToxicityAssessment)\n")
                f.write(f"Image: {result['metadata']['image_name']}\n")
                f.write(f"Extraction Time: {result['metadata']['extraction_timestamp']}\n")
                f.write(f"LLM Provider: {result['metadata']['llm_provider']}\n")
                f.write(f"Total Dimensions Found: {result['metadata']['total_dimensions_found']}\n\n")
                
                f.write("Extracted Dimensions:\n")
                f.write("-------------------\n")
                
                for i, dim in enumerate(result["dimensions"], 1):
                    f.write(f"{i}. {dim['class_name']}: {dim['label']}\n")
                    f.write(f"   Description: {dim['description']}\n")
                    f.write(f"   Method: {dim.get('extraction_method', 'N/A')}\n\n")
            else:
                f.write(f"Extraction failed: {result['metadata'].get('error', 'Unknown error')}\n")


# Convenience function
def extract_dimensions_from_image_reversed(
    image_path: Path,
    selected_dimensions: Optional[List[str]] = None,
    output_dir: Optional[Path] = None,
    llm_provider: str = "claude",
    additional_kb_paths: Optional[List[Path]] = None,
    iterative_kb: bool = False
) -> Dict[str, Any]:
    """
    Extract dimensions from a meme image using the reversed extraction order.
    
    Args:
        image_path: Path to the meme image
        selected_dimensions: List of dimension names to extract
        output_dir: Directory to save results
        llm_provider: LLM provider to use
        additional_kb_paths: Optional list of paths to additional knowledge base JSON-LD files
        iterative_kb: If True, attach additional KB to all prompts; if False, only to OverallIntent
        
    Returns:
        Extraction results dictionary
    """
    module = ReversedDimensionExtractionModule(llm_provider=llm_provider)
    return module.extract_dimensions_from_image(
        image_path, 
        selected_dimensions, 
        output_dir,
        additional_kb_paths=additional_kb_paths,
        iterative_kb=iterative_kb
    )

