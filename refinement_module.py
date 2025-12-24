"""
Refinement Module for Knowledge Graph Enhancement.

This module processes materializer prompts to add relations between individuals
in the generated knowledge graph.
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
import rdflib
from rdflib import Namespace, Literal, URIRef

from llm_integration import LLMManager
from scripts.py.extract_individuals_from_ttl import extract_individuals_by_dimension

logger = logging.getLogger(__name__)


class RefinementModule:
    """
    Module for refining knowledge graphs by adding relations between individuals.
    """
    
    def __init__(
        self,
        llm_provider: str = "huggingface",
        prompts_dir: Optional[Path] = None
    ):
        """
        Initialize the refinement module.
        
        Args:
            llm_provider: LLM provider to use ("claude" or "huggingface")
            prompts_dir: Directory containing materializer JSON-LD prompt files
        """
        self.llm_provider = llm_provider
        self.llm_manager = LLMManager()
        self.prompts_dir = prompts_dir or Path(__file__).parent / "prompts" / "refining-prompts"
        
        # Define namespaces
        self.EX = Namespace("http://example.org/multimodal-taxonomy#")
        self.RDFS = Namespace("http://www.w3.org/2000/01/rdf-schema#")
        self.RDF = Namespace("http://www.w3.org/1999/02/22-rdf-syntax-ns#")
        
        logger.info(f"Refinement module initialized with {llm_provider} provider")
    
    def refine_ontology(
        self,
        ttl_file: Path,
        image_path: Path,
        output_path: Path
    ) -> Dict[str, Any]:
        """
        Refine the ontology by processing all materializers.
        
        Args:
            ttl_file: Path to the input TTL file
            image_path: Path to the original image
            output_path: Path to save the refined TTL file
            
        Returns:
            Dictionary with refinement results
        """
        try:
            # Load the TTL file
            graph = rdflib.Graph()
            graph.parse(ttl_file, format="turtle")
            
            # Extract individuals by dimension
            dimensions_by_class = extract_individuals_by_dimension(ttl_file)
            
            logger.info(f"Extracted {len(dimensions_by_class)} dimension classes from TTL file")
            
            # Process each materializer
            materializers = [
                {
                    "name": "AnalogicalMappingRelationsMaterialiser",
                    "dimension": "AnalogicalMapping",
                    "related_dimensions": ["VisualMaterial", "TextualMaterial"],
                    "prompt_file": "AnalogicalMappingRelationsMaterialiser.jsonld"
                },
                {
                    "name": "EmotionRelationsMaterialised",
                    "dimension": "EmotionExpression",
                    "related_dimensions": ["VisualMaterial", "TextualMaterial", "Scene", "BackgroundKnowledge"],
                    "prompt_file": "EmotionRelationsMaterialised.jsonld"
                },
                {
                    "name": "SceneRelationsMaterialiser",
                    "dimension": "Scene",
                    "related_dimensions": ["VisualMaterial"],
                    "prompt_file": "SceneRelationsMaterialiser.jsonld"
                },
                {
                    "name": "ToxicityRelationsMaterialiser",
                    "dimension": "ToxicityAssessment",
                    "related_dimensions": ["VisualMaterial", "TextualMaterial", "Scene", "BackgroundKnowledge"],
                    "prompt_file": "ToxicityRelationMaterialiser.jsonld"
                }
            ]
            
            all_new_triples = []
            materializer_results = []
            
            for materializer in materializers:
                logger.info(f"Processing materializer: {materializer['name']}")
                
                result = self._process_materializer(
                    materializer,
                    dimensions_by_class,
                    graph,
                    image_path
                )
                
                if result["success"]:
                    all_new_triples.extend(result["triples"])
                    materializer_results.append({
                        "materializer": materializer["name"],
                        "triples_added": len(result["triples"]),
                        "triples": result.get("triples", []),
                        "relations": result.get("relations", []),
                        "success": True
                    })
                else:
                    materializer_results.append({
                        "materializer": materializer["name"],
                        "error": result.get("error"),
                        "success": False
                    })
            
            # Merge new triples with original TTL
            refined_ttl = self._merge_triples_with_ttl(ttl_file, all_new_triples)
            
            # Save refined TTL
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(refined_ttl)
            
            logger.info(f"Refined ontology saved to: {output_path}")
            
            # Save materializer LLM output JSON files (not the original prompts)
            saved_jsonld_files = []
            for i, materializer in enumerate(materializers):
                if i < len(materializer_results) and materializer_results[i].get("success"):
                    # Save the LLM response/relations as JSON
                    result_data = materializer_results[i]
                    if "relations" in result_data or "triples" in result_data:
                        json_output = output_path.parent / f"{output_path.stem}_{materializer['name']}_output.json"
                        output_data = {
                            "materializer": materializer["name"],
                            "dimension": materializer["dimension"],
                            "related_dimensions": materializer["related_dimensions"],
                            "relations": materializer_results[i].get("relations", []),
                            "triples": materializer_results[i].get("triples", []),
                            "triples_count": materializer_results[i].get("triples_added", 0)
                        }
                        with open(json_output, 'w', encoding='utf-8') as f:
                            json.dump(output_data, f, indent=2, ensure_ascii=False)
                        saved_jsonld_files.append(str(json_output))
                        logger.info(f"Saved materializer LLM output: {json_output}")
            
            return {
                "success": True,
                "output_file": str(output_path),
                "total_triples_added": len(all_new_triples),
                "materializer_results": materializer_results,
                "saved_jsonld_files": saved_jsonld_files
            }
            
        except Exception as e:
            logger.error(f"Error refining ontology: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e)
            }
    
    def _process_materializer(
        self,
        materializer: Dict[str, Any],
        dimensions_by_class: Dict[str, List[Dict[str, Any]]],
        graph: rdflib.Graph,
        image_path: Path
    ) -> Dict[str, Any]:
        """
        Process a single materializer.
        
        Args:
            materializer: Materializer configuration
            dimensions_by_class: Dictionary of individuals by dimension class
            graph: RDF graph
            image_path: Path to the image
            
        Returns:
            Dictionary with processing results
        """
        try:
            # Load materializer prompt
            prompt_file = self.prompts_dir / materializer["prompt_file"]
            if not prompt_file.exists():
                logger.warning(f"Materializer prompt file not found: {prompt_file}")
                return {"success": False, "error": f"Prompt file not found: {prompt_file}"}
            
            with open(prompt_file, 'r', encoding='utf-8') as f:
                prompt_data = json.load(f)
            
            prompt_text = prompt_data.get("promptExtractionText", "")
            if not prompt_text:
                logger.warning(f"No promptExtractionText found in {prompt_file}")
                return {"success": False, "error": "No promptExtractionText found"}
            
            # Get dimension individuals
            dimension_name = materializer["dimension"]
            dimension_individuals = dimensions_by_class.get(dimension_name, [])
            
            if not dimension_individuals:
                logger.info(f"No {dimension_name} individuals found, skipping materializer")
                return {"success": True, "triples": []}
            
            # Get related dimension individuals
            related_individuals = {}
            for related_dim in materializer["related_dimensions"]:
                related_individuals[related_dim] = dimensions_by_class.get(related_dim, [])
            
            # Always include OverallIntent individuals for all materializers
            overall_intent_individuals = dimensions_by_class.get("OverallIntent", [])
            if overall_intent_individuals:
                related_individuals["OverallIntent"] = overall_intent_individuals
            
            # Build full prompt
            full_prompt = self._build_materializer_prompt(
                prompt_text,
                dimension_individuals,
                related_individuals,
                graph
            )
            
            # Call LLM
            print(f"\n🤖 Calling LLM for {materializer['name']}...")
            print(f"   Provider: {self.llm_provider}")
            response = self.llm_manager.generate_response(
                full_prompt, 
                image_path, 
                provider=self.llm_provider
            )
            
            # Print LLM response for debugging
            print(f"\n📝 LLM Response for {materializer['name']}:")
            print("=" * 70)
            print(response)
            print("=" * 70)
            
            # Parse JSON response
            relations = self._parse_llm_response(response)
            print(f"✅ Parsed {len(relations)} relation(s) from response")
            if relations:
                print(f"   Relations: {json.dumps(relations, indent=2)}")
            
            # Convert to TTL triples
            triples = self._convert_relations_to_triples(relations, dimension_individuals, related_individuals)
            print(f"✅ Generated {len(triples)} TTL triple(s)")
            if triples:
                print("   Triples:")
                for triple in triples:
                    print(f"      {triple}")
            
            return {
                "success": True,
                "triples": triples,
                "relations": relations
            }
            
        except Exception as e:
            logger.error(f"Error processing materializer {materializer['name']}: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}
    
    def _build_materializer_prompt(
        self,
        prompt_text: str,
        dimension_individuals: List[Dict[str, Any]],
        related_individuals: Dict[str, List[Dict[str, Any]]],
        graph: rdflib.Graph
    ) -> str:
        """
        Build the full prompt for the materializer.
        
        Args:
            prompt_text: Base prompt text from JSON-LD
            dimension_individuals: List of individuals from the target dimension
            related_individuals: Dictionary of related individuals by dimension
            graph: RDF graph for extracting additional properties
            
        Returns:
            Full prompt string
        """
        prompt_parts = []
        
        # Add dimension individuals with all their properties
        prompt_parts.append("## Target Dimension Individuals\n")
        for individual in dimension_individuals:
            individual_info = self._get_individual_full_info(individual, graph)
            prompt_parts.append(f"### {individual['instance_name']}")
            prompt_parts.append(f"- Label: {individual.get('label', 'N/A')}")
            prompt_parts.append(f"- Description: {individual.get('description', 'N/A')}")
            if individual_info:
                prompt_parts.append(f"- Additional properties: {json.dumps(individual_info, indent=2)}")
            prompt_parts.append("")
        
        # Add related dimension individuals
        prompt_parts.append("## Related Dimension Individuals\n")
        # Always show OverallIntent first if present
        if "OverallIntent" in related_individuals and related_individuals["OverallIntent"]:
            prompt_parts.append("### OverallIntent")
            for individual in related_individuals["OverallIntent"]:
                prompt_parts.append(f"- {individual['instance_name']}: {individual.get('label', 'N/A')} - {individual.get('description', 'N/A')}")
            prompt_parts.append("")
        
        # Then show other related dimensions
        for dim_name, individuals in related_individuals.items():
            if dim_name != "OverallIntent" and individuals:
                prompt_parts.append(f"### {dim_name}")
                for individual in individuals:
                    prompt_parts.append(f"- {individual['instance_name']}: {individual.get('label', 'N/A')} - {individual.get('description', 'N/A')}")
                prompt_parts.append("")
        
        # Add the task prompt
        prompt_parts.append("## Task\n")
        prompt_parts.append(prompt_text)
        
        return "\n".join(prompt_parts)
    
    def _get_individual_full_info(
        self,
        individual: Dict[str, Any],
        graph: rdflib.Graph
    ) -> Dict[str, Any]:
        """
        Get all properties for an individual from the graph.
        
        Args:
            individual: Individual dictionary
            graph: RDF graph
            
        Returns:
            Dictionary with all properties
        """
        info = {}
        
        try:
            # Find the individual's URI
            instance_name = individual.get("instance_name", "")
            if not instance_name:
                return info
            
            # Try to find the subject in the graph
            subject_uri = None
            for subject, predicate, obj in graph.triples((None, self.RDF.type, None)):
                if isinstance(subject, URIRef) and instance_name in str(subject):
                    subject_uri = subject
                    break
            
            if not subject_uri:
                # Try constructing URI
                subject_uri = self.EX[instance_name]
            
            # Get all properties
            for predicate, obj in graph.predicate_objects(subject_uri):
                pred_name = str(predicate).split("#")[-1]
                if isinstance(obj, Literal):
                    info[pred_name] = str(obj)
                elif isinstance(obj, URIRef):
                    info[pred_name] = str(obj).split("#")[-1]
                else:
                    info[pred_name] = str(obj)
            
        except Exception as e:
            logger.debug(f"Error getting full info for {individual.get('instance_name')}: {e}")
        
        return info
    
    def _parse_llm_response(self, response: str) -> List[Dict[str, Any]]:
        """
        Parse JSON response from LLM.
        
        Args:
            response: LLM response string
            
        Returns:
            List of relation dictionaries
        """
        try:
            # Try to extract JSON from response
            # Look for JSON array pattern
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                relations = json.loads(json_str)
                return relations if isinstance(relations, list) else [relations]
            
            # Try parsing entire response as JSON
            relations = json.loads(response)
            return relations if isinstance(relations, list) else [relations]
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.debug(f"Response was: {response[:500]}")
            return []
    
    def _normalize_identifier(self, identifier: str) -> str:
        """
        Normalize an identifier to valid Turtle syntax.
        
        Args:
            identifier: Identifier string (may contain spaces, special chars)
            
        Returns:
            Normalized identifier (underscores, no spaces, valid Turtle)
        """
        if not identifier:
            return ""
        
        # Remove leading/trailing whitespace
        identifier = identifier.strip()
        
        # Replace spaces and special characters with underscores
        import re
        # Replace spaces, hyphens, and other special chars with underscores
        identifier = re.sub(r'[^\w]', '_', identifier)
        # Remove multiple consecutive underscores
        identifier = re.sub(r'_+', '_', identifier)
        # Remove leading/trailing underscores
        identifier = identifier.strip('_')
        
        # Ensure it starts with a letter or underscore (Turtle requirement)
        if identifier and not re.match(r'^[a-zA-Z_]', identifier):
            identifier = '_' + identifier
        
        return identifier
    
    def _convert_relations_to_triples(
        self,
        relations: List[Dict[str, Any]],
        dimension_individuals: List[Dict[str, Any]],
        related_individuals: Dict[str, List[Dict[str, Any]]]
    ) -> List[str]:
        """
        Convert relation dictionaries to TTL triple strings.
        
        Args:
            relations: List of relation dictionaries from LLM
            dimension_individuals: List of target dimension individuals
            related_individuals: Dictionary of related individuals
            
        Returns:
            List of TTL triple strings
        """
        triples = []
        
        # Create lookup maps
        all_individuals = {}
        for ind in dimension_individuals:
            all_individuals[ind["instance_name"]] = ind
        for dim_inds in related_individuals.values():
            for ind in dim_inds:
                all_individuals[ind["instance_name"]] = ind
        
        for relation in relations:
            # Handle different relation formats based on materializer
            
            # AnalogicalMapping format
            if "mapping" in relation:
                mapping_id = self._normalize_identifier(relation.get("mapping", ""))
                if not mapping_id:
                    continue
                    
                if "hasMappedEntity" in relation:
                    mapped_entity = self._normalize_identifier(relation["hasMappedEntity"])
                    if mapped_entity:
                        triples.append(f":{mapping_id} :hasMappedEntity :{mapped_entity} .")
                if "hasMappingEntity" in relation:
                    mapping_entity = self._normalize_identifier(relation["hasMappingEntity"])
                    if mapping_entity:
                        triples.append(f":{mapping_id} :hasMappingEntity :{mapping_entity} .")
                if "mappedOnto" in relation:
                    mapped_onto = self._normalize_identifier(relation["mappedOnto"])
                    if mapped_onto:
                        triples.append(f":{mapping_id} :mappedOnto :{mapped_onto} .")
            
            # Emotion format
            elif "emotion" in relation:
                emotion_id = self._normalize_identifier(relation.get("emotion", ""))
                if not emotion_id:
                    continue
                    
                if "expressors" in relation:
                    for expressor in relation["expressors"]:
                        entity = self._normalize_identifier(expressor.get("entity", ""))
                        rel_type = self._normalize_identifier(expressor.get("relation", "hasExpressor"))
                        if entity and rel_type:
                            triples.append(f":{emotion_id} :{rel_type} :{entity} .")
                if "directRelations" in relation:
                    for direct_rel in relation["directRelations"]:
                        from_entity = self._normalize_identifier(direct_rel.get("from", ""))
                        to_entity = self._normalize_identifier(direct_rel.get("to", ""))
                        rel_type = self._normalize_identifier(direct_rel.get("relation", ""))
                        if from_entity and to_entity and rel_type:
                            triples.append(f":{from_entity} :{rel_type} :{to_entity} .")
            
            # Scene format
            elif "scene" in relation:
                scene_id = self._normalize_identifier(relation.get("scene", ""))
                if not scene_id:
                    continue
                    
                if "participants" in relation:
                    for participant in relation["participants"]:
                        entity = self._normalize_identifier(participant.get("entity", ""))
                        rel_type = self._normalize_identifier(participant.get("relation", "hasParticipant"))
                        if entity and rel_type:
                            triples.append(f":{scene_id} :{rel_type} :{entity} .")
                if "directRelations" in relation:
                    for direct_rel in relation["directRelations"]:
                        from_entity = self._normalize_identifier(direct_rel.get("from", ""))
                        to_entity = self._normalize_identifier(direct_rel.get("to", ""))
                        rel_type = self._normalize_identifier(direct_rel.get("relation", ""))
                        if from_entity and to_entity and rel_type:
                            triples.append(f":{from_entity} :{rel_type} :{to_entity} .")
            
            # Toxicity format
            elif "toxicity" in relation:
                toxicity_id = self._normalize_identifier(relation.get("toxicity", ""))
                if not toxicity_id:
                    continue
                    
                if "hasToxicElement" in relation:
                    toxic_element = self._normalize_identifier(relation["hasToxicElement"])
                    if toxic_element:
                        triples.append(f":{toxicity_id} :hasToxicElement :{toxic_element} .")
            
            # Generic format: direct relations (for AnalogicalMapping mappedOnto pattern)
            elif "from" in relation and "to" in relation and "relation" in relation:
                from_entity = self._normalize_identifier(relation["from"])
                to_entity = self._normalize_identifier(relation["to"])
                rel_type = self._normalize_identifier(relation["relation"])
                if from_entity and to_entity and rel_type:
                    triples.append(f":{from_entity} :{rel_type} :{to_entity} .")
            
            # Generic format: other patterns
            else:
                # Look for common relation patterns
                for key, value in relation.items():
                    if key not in ["from", "to", "relation", "subject", "entity"] and isinstance(value, str):
                        # Assume key is a property name
                        subject = relation.get("from") or relation.get("subject") or relation.get("entity")
                        if subject:
                            subject = self._normalize_identifier(subject)
                            value = self._normalize_identifier(value)
                            key = self._normalize_identifier(key)
                            if subject and value and key:
                                triples.append(f":{subject} :{key} :{value} .")
        
        return triples
    
    def _merge_triples_with_ttl(
        self,
        original_ttl_file: Path,
        new_triples: List[str]
    ) -> str:
        """
        Merge new triples with the original TTL file.
        
        Args:
            original_ttl_file: Path to original TTL file
            new_triples: List of new TTL triple strings
            
        Returns:
            Merged TTL content
        """
        # Read original TTL
        with open(original_ttl_file, 'r', encoding='utf-8') as f:
            original_ttl = f.read()
        
        # Append new triples section
        if new_triples:
            merged_ttl = original_ttl + "\n\n"
            merged_ttl += "#################################################################\n"
            merged_ttl += "#    Refined Relations (from Materializers)\n"
            merged_ttl += "#################################################################\n\n"
            
            for triple in new_triples:
                merged_ttl += triple + "\n"
        else:
            merged_ttl = original_ttl
        
        return merged_ttl

