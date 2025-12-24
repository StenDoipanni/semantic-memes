"""
Q&A Generation Module.

This module generates question-answer pairs based on extracted meme dimensions.
It takes the individual dimension JSON-LD files and creates Q&A pairs for each dimension.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
import uuid
from datetime import datetime
import rdflib
from rdflib import Namespace, Literal
from rdflib.namespace import RDF, RDFS

from llm_integration import LLMProvider, ClaudeProvider, HuggingFaceProvider
from ontology_loader import OntologyLoader
from config import LLMConfig, OntologyConfig

logger = logging.getLogger(__name__)


class QAGenerationModule:
    """
    Module for generating Q&A pairs from extracted meme dimensions.
    """
    
    def __init__(self, llm_provider: str = "claude"):
        """
        Initialize the Q&A generation module.
        
        Args:
            llm_provider: LLM provider to use ("claude" or "huggingface")
        """
        self.llm_provider = llm_provider
        self.llm = self._initialize_llm()
        self.ontology_loader = OntologyLoader()
        
        logger.info(f"Q&A generation module initialized with {llm_provider} provider")
    
    def _initialize_llm(self) -> LLMProvider:
        """Initialize the LLM provider."""
        if self.llm_provider == "claude":
            return ClaudeProvider()
        elif self.llm_provider == "huggingface":
            from config import LLMConfig
            return HuggingFaceProvider(token=LLMConfig.HUGGINGFACE_TOKEN)
        else:
            raise ValueError(f"Unsupported LLM provider: {self.llm_provider}")
    
    def generate_qa_for_dimension(
        self,
        dimension_name: str,
        dimension_files: List[Path],
        image_path: Path,
        output_dir: Path
    ) -> Dict[str, Any]:
        """
        Generate Q&A pairs for a specific dimension.
        
        Args:
            dimension_name: Name of the dimension
            dimension_files: List of JSON-LD files for this dimension
            image_path: Path to the original meme image
            output_dir: Output directory for Q&A files
            
        Returns:
            Dictionary with generation results
        """
        try:
            logger.info(f"Generating Q&A for dimension: {dimension_name}")
            
            # Load dimension instances
            dimension_instances = self._load_dimension_instances(dimension_files)
            # Note: We allow empty instances - Q&A can be generated from dimension description alone
            if not dimension_instances:
                logger.warning(f"No dimension instances found for {dimension_name}, will use dimension description only")
            
            # Get dimension info from ontology
            dimension_info = self._get_dimension_info(dimension_name)
            
            # Generate Q&A prompt
            prompt = self._create_qa_prompt(dimension_name, dimension_instances, dimension_info)
            
            # Generate Q&A using LLM
            response = self.llm.generate_response(prompt, image_path)
            
            # Parse Q&A response
            qa_data = self._parse_qa_response(response, dimension_name, dimension_instances)
            
            # Save Q&A files
            saved_files = self._save_qa_files(qa_data, dimension_name, image_path, output_dir)
            
            return {
                "success": True,
                "dimension": dimension_name,
                "qa_pairs": len(qa_data.get("qa_pairs", [])),
                "saved_files": saved_files
            }
            
        except Exception as e:
            logger.error(f"Error generating Q&A for {dimension_name}: {e}")
            return {"success": False, "error": str(e)}
    
    def generate_qa_for_dimension_from_ttl(
        self,
        dimension_name: str,
        ttl_file: Path,
        image_path: Path,
        output_dir: Path,
        questions_per_dimension: int = 1
    ) -> Dict[str, Any]:
        """
        Generate Q&A pairs for a specific dimension directly from TTL file.
        
        Args:
            dimension_name: Name of the dimension
            ttl_file: Path to the TTL ontology file
            image_path: Path to the original meme image
            output_dir: Output directory for Q&A files
            questions_per_dimension: Number of questions to generate per dimension (default: 1)
            
        Returns:
            Dictionary with generation results
        """
        try:
            logger.info(f"Generating {questions_per_dimension} Q&A pair(s) for dimension: {dimension_name} from TTL file")
            
            # Extract individuals for this dimension from TTL
            dimension_instances = self._extract_individuals_from_ttl(ttl_file, dimension_name)
            
            # Get dimension info from ontology
            dimension_info = self._get_dimension_info(dimension_name)
            
            # Generate Q&A prompt (handles empty instances)
            prompt = self._create_qa_prompt(dimension_name, dimension_instances, dimension_info, questions_per_dimension)
            
            # Generate Q&A using LLM
            response = self.llm.generate_response(prompt, image_path)
            
            # Parse Q&A response (pass dimension_instances to populate related_instances)
            qa_data_list = self._parse_qa_response(response, dimension_name, dimension_instances, questions_per_dimension)
            
            # Save Q&A files for each Q&A pair
            saved_files = []
            for qa_data in qa_data_list:
                files = self._save_qa_files(qa_data, dimension_name, image_path, output_dir)
                saved_files.append(files)
            
            return {
                "success": True,
                "dimension": dimension_name,
                "qa_pairs": len(qa_data_list),
                "saved_files": saved_files,
                "instances_count": len(dimension_instances)
            }
            
        except Exception as e:
            logger.error(f"Error generating Q&A for {dimension_name} from TTL: {e}")
            return {"success": False, "error": str(e)}
    
    def get_standard_dimensions(self) -> List[str]:
        """
        Get the standard list of dimensions from config, with name corrections for TTL files.
        Maps config dimension names to their actual names in TTL files.
        
        Returns:
            List of dimension class names as they appear in TTL files
        """
        from config import OntologyConfig
        
        # Mapping from config names to TTL file names
        # This handles cases where config uses different names than TTL files
        dimension_name_mapping = {
            "Toxicity": "ToxicityAssessment",  # Config uses "Toxicity", TTL uses "ToxicityAssessment"
            # Add other mappings here if needed
        }
        
        standard_dims = []
        for config_dim in OntologyConfig.DIMENSION_CLASSES:
            # Use mapped name if available, otherwise use config name
            ttl_dim_name = dimension_name_mapping.get(config_dim, config_dim)
            standard_dims.append(ttl_dim_name)
        
        logger.info(f"Standard dimensions list (mapped from config): {standard_dims}")
        return standard_dims
    
    def get_dimensions_from_ttl(self, ttl_file: Path) -> List[str]:
        """
        Extract dimension class names directly from a TTL file.
        This uses the TTL file as the source of truth for dimension names.
        
        Args:
            ttl_file: Path to the TTL file
            
        Returns:
            List of dimension class names found in the TTL file
        """
        dimension_classes = set()
        
        try:
            # Load the TTL file
            g = rdflib.Graph()
            g.parse(ttl_file, format="turtle")
            
            # Define namespaces
            EX = Namespace("http://example.org/multimodal-taxonomy#")
            RDF = Namespace("http://www.w3.org/1999/02/22-rdf-syntax-ns#")
            
            # Find all dimension classes that have instances in this TTL file
            for subject, predicate, obj in g.triples((None, RDF.type, None)):
                if isinstance(obj, rdflib.URIRef) and str(obj).startswith(str(EX)):
                    class_name = str(obj).split("#")[-1]
                    # Check if it's a dimension class (capitalized, not a property)
                    if (class_name[0].isupper() and 
                        class_name not in ['Class', 'ObjectProperty', 'AnnotationProperty', 'Ontology'] and
                        not class_name.startswith('dimension') and
                        not class_name.startswith('relation')):
                        # Verify this class has at least one instance
                        instances = list(g.triples((None, RDF.type, obj)))
                        if instances:
                            dimension_classes.add(class_name)
            
            logger.info(f"Found {len(dimension_classes)} dimension classes in TTL file: {sorted(dimension_classes)}")
            return sorted(list(dimension_classes))
            
        except Exception as e:
            logger.error(f"Error extracting dimensions from TTL file {ttl_file}: {e}")
            return []
    
    def _extract_individuals_from_ttl(
        self,
        ttl_file: Path,
        dimension_name: str
    ) -> List[Dict[str, Any]]:
        """
        Extract individuals for a specific dimension from a TTL file.
        
        Args:
            ttl_file: Path to the TTL file
            dimension_name: Name of the dimension class to extract
            
        Returns:
            List of individual dictionaries with instance_name, label, and description
        """
        instances = []
        
        try:
            # Load the TTL file
            g = rdflib.Graph()
            g.parse(ttl_file, format="turtle")
            
            # Define namespaces
            EX = Namespace("http://example.org/multimodal-taxonomy#")
            RDFS = Namespace("http://www.w3.org/2000/01/rdf-schema#")
            RDF = Namespace("http://www.w3.org/1999/02/22-rdf-syntax-ns#")
            
            # Find the dimension class URI
            dimension_class_uri = EX[dimension_name]
            
            # Find all individuals of this dimension class
            processed_instances = set()
            
            for subject, predicate, obj in g.triples((None, RDF.type, dimension_class_uri)):
                if isinstance(subject, rdflib.URIRef) and subject not in processed_instances:
                    processed_instances.add(subject)
                    instance_name = subject.split("#")[-1]
                    
                    # Get label
                    label = None
                    for _, _, label_obj in g.triples((subject, RDFS.label, None)):
                        if isinstance(label_obj, Literal):
                            label = str(label_obj)
                            break
                    
                    # Get description (rdfs:comment)
                    description = None
                    for _, _, desc_obj in g.triples((subject, RDFS.comment, None)):
                        if isinstance(desc_obj, Literal):
                            description = str(desc_obj)
                            break
                    
                    # Only add if we have at least label and description
                    if label and description:
                        instances.append({
                            "instance_name": instance_name,
                            "label": label,
                            "description": description
                        })
                        logger.debug(f"Extracted instance: {instance_name} ({label})")
            
            logger.info(f"Extracted {len(instances)} individuals for dimension {dimension_name}")
            return instances
            
        except Exception as e:
            logger.error(f"Error extracting individuals from TTL file {ttl_file} for {dimension_name}: {e}")
            return []
    
    def _load_dimension_instances(self, dimension_files: List[Path]) -> List[Dict[str, Any]]:
        """Load dimension instances from JSON-LD files."""
        instances = []
        
        logger.info(f"Loading {len(dimension_files)} dimension files")
        for file_path in dimension_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    instance_data = {
                        "instance_name": data.get("instance_name", ""),
                        "label": data.get("label", ""),
                        "description": data.get("description", "")
                    }
                    instances.append(instance_data)
                    logger.debug(f"Loaded instance from {file_path.name}: {instance_data['instance_name']}")
            except Exception as e:
                logger.error(f"Error loading dimension file {file_path}: {e}")
                continue
        
        logger.info(f"Loaded {len(instances)} dimension instances")
        return instances
    
    def _get_dimension_info(self, dimension_name: str) -> Dict[str, str]:
        """Get dimension information from ontology."""
        try:
            # Get dimension classes from the loaded ontology
            dimension_classes = self.ontology_loader.get_dimension_classes()
            
            # Find the specific dimension
            for dim_class in dimension_classes:
                if dim_class["name"] == dimension_name:
                    properties = dim_class.get("properties", {})
                    return {
                        "name": dimension_name,
                        "label": properties.get("label", dimension_name),
                        "description": properties.get("comment", f"Dimension: {dimension_name}")
                    }
            
            # If not found in dimension classes, return default
            return {
                "name": dimension_name,
                "label": dimension_name,
                "description": f"Dimension: {dimension_name}"
            }
        except Exception as e:
            logger.warning(f"Could not load dimension info for {dimension_name}: {e}")
            return {
                "name": dimension_name,
                "label": dimension_name,
                "description": f"Dimension: {dimension_name}"
            }
    
    def _create_qa_prompt(
        self,
        dimension_name: str,
        dimension_instances: List[Dict[str, Any]],
        dimension_info: Dict[str, str],
        questions_per_dimension: int = 1
    ) -> str:
        """Create the Q&A generation prompt."""
        
        # Build dimension instances context
        instances_context = ""
        if dimension_instances:
            instances_context = "FOCUS ON THESE SPECIFIC ELEMENTS IN Q&A GENERATION:\n\n"
            for i, instance in enumerate(dimension_instances, 1):
                instances_context += f"{i}. Instance Name: {instance['instance_name']}\n"
                instances_context += f"   Label: {instance['label']}\n"
                instances_context += f"   Description: {instance['description']}\n\n"
        else:
            instances_context = "No specific individuals were extracted for this dimension. Generate Q&A based on the general dimension description.\n\n"
        
        # Adjust instructions based on whether we have instances
        if dimension_instances:
            qa_instructions = """1. Be directly related to the extracted dimension individuals listed below
2. Focus specifically on the instances provided
3. Be clear and specific"""
            related_note = "The Q&A should be based on the dimension instances provided below."
        else:
            qa_instructions = """1. Be directly related to the dimension description provided
2. Focus on general aspects of this dimension in the meme
3. Be clear and specific"""
            related_note = "The Q&A should be based on the general dimension description, as no specific instances were extracted."
        
        question_text = "question-answer pair (Q&A)" if questions_per_dimension == 1 else f"{questions_per_dimension} question-answer pairs (Q&A)"
        generate_text = "generate a" if questions_per_dimension == 1 else f"generate exactly {questions_per_dimension}"
        
        # Prepare JSON format indicators (avoid backslash in f-string)
        json_start = "{" if questions_per_dimension == 1 else "["
        json_end = "}" if questions_per_dimension == 1 else "]"
        json_end_with_note = "}" if questions_per_dimension == 1 else ", ... (repeat for each Q&A pair)\n]"
        generate_instruction = "a Q&A pair" if questions_per_dimension == 1 else f"exactly {questions_per_dimension} Q&A pairs"
        related_instances_json = json.dumps([inst['instance_name'] for inst in dimension_instances]) if dimension_instances else "[]"
        
        prompt = f"""Consider the attached meme (M) and {generate_text} {question_text} about the {dimension_info['label']} dimension.

The Q&A pair should:

{qa_instructions}
4. Have 4 possible answers with similar length and complexity:
   a. One correct answer (based on the dimension information)
   b. One plausible but incorrect answer (related but wrong)
   c. One implausible answer (clearly wrong but not obviously so)
   d. One answer which says "None of the others"

CRITICAL REQUIREMENTS:
- Make ALL answers similar in length (2-8 words each)
- Randomize the order of answers (correct answer should NOT be always first)
- Ensure the correct answer is not obviously longer or more detailed
- Make plausible and implausible answers equally convincing in length

DIMENSION CONTEXT:
Dimension Name: {dimension_info['name']}
Dimension Label: {dimension_info['label']}
Dimension Description: {dimension_info['description']}

{instances_context}
{related_note}

Please generate {generate_instruction} in the following JSON format:
{json_start}
{{
  "question": "Your question here",
  "answers": [
    {{
      "text": "Short answer option 1",
      "is_correct": true/false
    }},
    {{
      "text": "Short answer option 2", 
      "is_correct": true/false
    }},
    {{
      "text": "Short answer option 3",
      "is_correct": true/false
    }},
    {{
      "text": "Short answer option 4",
      "is_correct": true/false
    }}
  ],
  "explanation": "Brief explanation of the correct answer",
  "dimension": "{dimension_name}",
  "related_instances": {related_instances_json}
}}
{json_end_with_note}

IMPORTANT: 
- Randomize the answer order for each question and keep all answers concise and similar in length
- Each question should explore different aspects of the dimension
- Make sure questions are diverse and not repetitive"""
        
        return prompt
    
    def _parse_qa_response(
        self, 
        response: str, 
        dimension_name: str, 
        dimension_instances: Optional[List[Dict[str, Any]]] = None,
        questions_per_dimension: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Parse the LLM response to extract Q&A data.
        
        Args:
            response: LLM response string
            dimension_name: Name of the dimension
            dimension_instances: List of dimension instances from TTL file (used to populate related_instances)
            questions_per_dimension: Number of questions expected
            
        Returns:
            List of dictionaries with parsed Q&A data
        """
        try:
            # Try to extract JSON from response (could be single object or array)
            import re
            # First try to find array pattern
            array_match = re.search(r'\[.*\]', response, re.DOTALL)
            if array_match:
                try:
                    qa_data_list = json.loads(array_match.group())
                    if not isinstance(qa_data_list, list):
                        qa_data_list = [qa_data_list]
                except:
                    qa_data_list = None
            else:
                qa_data_list = None
            
            # If no array, try single object
            if qa_data_list is None:
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    qa_data = json.loads(json_match.group())
                    qa_data_list = [qa_data] if not isinstance(qa_data, list) else qa_data
                else:
                    qa_data_list = []
            
            # Ensure we have the right number of Q&A pairs
            while len(qa_data_list) < questions_per_dimension:
                qa_data_list.append({
                    "question": "Generated question based on dimension analysis",
                    "answers": [
                        {"text": "Correct answer", "is_correct": True},
                        {"text": "Plausible answer", "is_correct": False},
                        {"text": "Implausible answer", "is_correct": False},
                        {"text": "None of the above", "is_correct": False}
                    ],
                    "explanation": "Explanation of the correct answer",
                    "dimension": dimension_name,
                    "related_instances": []
                })
            
            # Limit to requested number
            qa_data_list = qa_data_list[:questions_per_dimension]
            
            # Process each Q&A pair
            processed_list = []
            for qa_data in qa_data_list:
                # IMPORTANT: Replace related_instances with actual instance names from TTL file
                if dimension_instances:
                    qa_data["related_instances"] = [inst["instance_name"] for inst in dimension_instances]
                else:
                    qa_data["related_instances"] = []
                
                # Post-process: Shuffle answers if correct answer is first
                if "answers" in qa_data and len(qa_data["answers"]) >= 2:
                    qa_data["answers"] = self._shuffle_answers(qa_data["answers"])
                
                # Add metadata
                qa_data["generation_timestamp"] = datetime.now().isoformat()
                qa_data["generation_method"] = f"{self.llm_provider}_api"
                qa_data["qa_id"] = str(uuid.uuid4())
                
                processed_list.append(qa_data)
            
            logger.info(f"Parsed {len(processed_list)} Q&A pair(s) for {dimension_name}")
            return processed_list
            
        except Exception as e:
            logger.error(f"Error parsing Q&A response: {e}")
            # Return fallback structure(s)
            # Use actual instance names from TTL if available
            related_instances = []
            if dimension_instances:
                related_instances = [inst["instance_name"] for inst in dimension_instances]
            
            fallback_list = []
            for i in range(questions_per_dimension):
                fallback_list.append({
                    "question": f"Generated question {i+1} based on dimension analysis",
                    "answers": [
                        {"text": "Correct answer", "is_correct": True},
                        {"text": "Plausible answer", "is_correct": False},
                        {"text": "Implausible answer", "is_correct": False},
                        {"text": "None of the above", "is_correct": False}
                    ],
                    "explanation": "Explanation of the correct answer",
                    "dimension": dimension_name,
                    "related_instances": related_instances,
                    "generation_timestamp": datetime.now().isoformat(),
                    "generation_method": f"{self.llm_provider}_api",
                    "qa_id": str(uuid.uuid4()),
                    "error": str(e)
                })
            
            return fallback_list
    
    def _save_qa_files(
        self,
        qa_data: Dict[str, Any],
        dimension_name: str,
        image_path: Path,
        output_dir: Path
    ) -> Dict[str, str]:
        """Save Q&A files in JSON-LD and text formats."""
        saved_files = {}
        
        try:
            # Create Q&A directory with image name prefix
            # Use [image_name]_qa/dimension_name structure
            image_name = image_path.stem
            qa_subdir_name = f"{image_name}_qa"
            
            # If output_dir already ends with "_qa", use it directly
            if output_dir.name.endswith("_qa"):
                qa_dir = output_dir / dimension_name
            else:
                qa_dir = output_dir / qa_subdir_name / dimension_name
            qa_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate base filename
            base_name = image_path.stem
            qa_id = qa_data.get("qa_id", str(uuid.uuid4()))
            
            # Save JSON-LD file
            jsonld_path = qa_dir / f"{base_name}_{dimension_name}_qa_{qa_id[:8]}.jsonld"
            jsonld_data = self._create_qa_jsonld(qa_data, image_path)
            with open(jsonld_path, 'w', encoding='utf-8') as f:
                json.dump(jsonld_data, f, indent=2, ensure_ascii=False)
            saved_files["jsonld"] = str(jsonld_path)
            
            # Save text file
            text_path = qa_dir / f"{base_name}_{dimension_name}_qa_{qa_id[:8]}.txt"
            with open(text_path, 'w', encoding='utf-8') as f:
                f.write(f"Q&A Pair for {dimension_name}\n")
                f.write("=" * 50 + "\n\n")
                f.write(f"Question: {qa_data['question']}\n\n")
                f.write("Answers:\n")
                for i, answer in enumerate(qa_data['answers'], 1):
                    correct_marker = " ✓" if answer.get('is_correct') else ""
                    f.write(f"{i}. {answer['text']}{correct_marker}\n")
                f.write(f"\nExplanation: {qa_data.get('explanation', 'No explanation provided')}\n")
                f.write(f"\nDimension: {qa_data.get('dimension', dimension_name)}\n")
                related_instances = qa_data.get('related_instances', [])
                if related_instances:
                    f.write(f"\nRelated Instances (from TTL file): {', '.join(related_instances)}\n")
                else:
                    f.write(f"\nRelated Instances: None (Q&A generated from dimension description only)\n")
                f.write(f"Generated: {qa_data.get('generation_timestamp', 'Unknown')}\n")
            saved_files["text"] = str(text_path)
            
            logger.info(f"Saved Q&A files for {dimension_name}")
            
        except Exception as e:
            logger.error(f"Error saving Q&A files for {dimension_name}: {e}")
        
        return saved_files
    
    def _create_qa_jsonld(self, qa_data: Dict[str, Any], image_path: Path) -> Dict[str, Any]:
        """Create JSON-LD structure for Q&A data."""
        qa_id = qa_data.get("qa_id", str(uuid.uuid4()))
        
        jsonld = {
            "@context": {
                "@vocab": "http://example.org/multimodal-taxonomy#",
                "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
                "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
                "owl": "http://www.w3.org/2002/07/owl#"
            },
            "@id": f"http://example.org/multimodal-taxonomy#qa_{qa_id}",
            "@type": "QuestionAnswerPair",
            "question": qa_data["question"],
            "answers": qa_data["answers"],
            "explanation": qa_data.get("explanation", ""),
            "dimension": qa_data.get("dimension", ""),
            "relatedInstances": qa_data.get("related_instances", []),
            "generationTimestamp": qa_data.get("generation_timestamp", ""),
            "generationMethod": qa_data.get("generation_method", ""),
            "sourceImage": {
                "@id": f"http://example.org/multimodal-taxonomy#image_{image_path.stem}",
                "@type": "Image",
                "filename": image_path.name,
                "path": str(image_path)
            }
        }
        
        return jsonld
    
    def _shuffle_answers(self, answers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Shuffle answers to ensure the correct answer is not always first.
        
        Args:
            answers: List of answer dictionaries
            
        Returns:
            Shuffled list of answers
        """
        import random
        
        # Check if correct answer is first
        if answers and answers[0].get("is_correct", False):
            # Shuffle the answers
            shuffled = answers.copy()
            random.shuffle(shuffled)
            logger.info("Shuffled answers to prevent correct answer from being first")
            return shuffled
        
        return answers


def generate_qa_for_image(
    image_path: Path,
    dimensions_dir: Path,
    output_dir: Path,
    llm_provider: str = "claude"
) -> Dict[str, Any]:
    """
    Generate Q&A pairs for all dimensions of an image.
    
    Args:
        image_path: Path to the meme image
        dimensions_dir: Directory containing dimension folders
        output_dir: Output directory for Q&A files
        llm_provider: LLM provider to use
        
    Returns:
        Dictionary with generation results
    """
    qa_module = QAGenerationModule(llm_provider)
    results = {
        "success": True,
        "image_path": str(image_path),
        "dimensions_processed": [],
        "total_qa_pairs": 0,
        "errors": []
    }
    
    # Get all dimension folders
    if not dimensions_dir.exists():
        logger.error(f"Dimensions directory not found: {dimensions_dir}")
        return {"success": False, "error": "Dimensions directory not found"}
    
    dimension_folders = [d for d in dimensions_dir.iterdir() if d.is_dir()]
    
    if not dimension_folders:
        logger.warning(f"No dimension folders found in {dimensions_dir}")
        return {"success": False, "error": "No dimension folders found"}
    
    logger.info(f"Found {len(dimension_folders)} dimension folders")
    
    for dimension_folder in dimension_folders:
        dimension_name = dimension_folder.name
        
        # Get all JSON-LD files in this dimension folder
        dimension_files = list(dimension_folder.glob("*.jsonld"))
        
        if not dimension_files:
            logger.warning(f"No JSON-LD files found in {dimension_folder}")
            results["errors"].append(f"No files found for {dimension_name}")
            continue
        
        logger.info(f"Processing {dimension_name} with {len(dimension_files)} files")
        
        # Generate Q&A for this dimension
        qa_result = qa_module.generate_qa_for_dimension(
            dimension_name, dimension_files, image_path, output_dir
        )
        
        if qa_result["success"]:
            results["dimensions_processed"].append(dimension_name)
            results["total_qa_pairs"] += qa_result.get("qa_pairs", 0)
            logger.info(f"Successfully generated Q&A for {dimension_name}")
        else:
            error_msg = f"Failed to generate Q&A for {dimension_name}: {qa_result.get('error', 'Unknown error')}"
            results["errors"].append(error_msg)
            logger.error(error_msg)
    
    return results
