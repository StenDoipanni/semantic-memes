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
            return HuggingFaceProvider()
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
            if not dimension_instances:
                logger.warning(f"No dimension instances found for {dimension_name}")
                return {"success": False, "error": "No dimension instances found"}
            
            # Get dimension info from ontology
            dimension_info = self._get_dimension_info(dimension_name)
            
            # Generate Q&A prompt
            prompt = self._create_qa_prompt(dimension_name, dimension_instances, dimension_info)
            
            # Generate Q&A using LLM
            response = self.llm.generate_response(prompt, image_path)
            
            # Parse Q&A response
            qa_data = self._parse_qa_response(response, dimension_name)
            
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
    
    def _load_dimension_instances(self, dimension_files: List[Path]) -> List[Dict[str, Any]]:
        """Load dimension instances from JSON-LD files."""
        instances = []
        
        for file_path in dimension_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    instances.append({
                        "instance_name": data.get("instance_name", ""),
                        "label": data.get("label", ""),
                        "description": data.get("description", "")
                    })
            except Exception as e:
                logger.error(f"Error loading dimension file {file_path}: {e}")
                continue
        
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
        dimension_info: Dict[str, str]
    ) -> str:
        """Create the Q&A generation prompt."""
        
        # Build dimension instances context
        instances_context = ""
        for i, instance in enumerate(dimension_instances, 1):
            instances_context += f"{i}. Instance Name: {instance['instance_name']}\n"
            instances_context += f"   Label: {instance['label']}\n"
            instances_context += f"   Description: {instance['description']}\n\n"
        
        prompt = f"""Consider the attached meme (M) and the dimensions graph (D) provided in the json-ld attached file.

Generate one question-answer pair (Q&A). The Q&A pair should:

1. Be directly related to the extracted dimensions individuals
2. Be clear and specific
3. Have 4 possible answers with similar length and complexity:
   a. One correct answer (based on the dimension instances)
   b. One plausible but incorrect answer (related but wrong)
   c. One implausible answer (clearly wrong but not obviously so)
   d. One answer which says "None of the above"

CRITICAL REQUIREMENTS:
- Make ALL answers similar in length (2-8 words each)
- Randomize the order of answers (correct answer should NOT be always first)
- Ensure the correct answer is not obviously longer or more detailed
- Make plausible and implausible answers equally convincing in length

DIMENSION CONTEXT:
Dimension Name: {dimension_info['name']}
Dimension Label: {dimension_info['label']}
Dimension Description: {dimension_info['description']}

DIMENSION INSTANCES:
{instances_context}

Please generate a Q&A pair in the following JSON format:
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
  "related_instances": ["instance1", "instance2"]
}}

IMPORTANT: Randomize the answer order and keep all answers concise and similar in length."""
        
        return prompt
    
    def _parse_qa_response(self, response: str, dimension_name: str) -> Dict[str, Any]:
        """Parse the LLM response to extract Q&A data."""
        try:
            # Try to extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                qa_data = json.loads(json_match.group())
            else:
                # Fallback: create basic structure
                qa_data = {
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
                }
            
            # Post-process: Shuffle answers if correct answer is first
            if "answers" in qa_data and len(qa_data["answers"]) >= 2:
                qa_data["answers"] = self._shuffle_answers(qa_data["answers"])
            
            # Add metadata
            qa_data["generation_timestamp"] = datetime.now().isoformat()
            qa_data["generation_method"] = f"{self.llm_provider}_api"
            qa_data["qa_id"] = str(uuid.uuid4())
            
            return qa_data
            
        except Exception as e:
            logger.error(f"Error parsing Q&A response: {e}")
            # Return fallback structure
            return {
                "question": "Generated question based on dimension analysis",
                "answers": [
                    {"text": "Correct answer", "is_correct": True},
                    {"text": "Plausible answer", "is_correct": False},
                    {"text": "Implausible answer", "is_correct": False},
                    {"text": "None of the above", "is_correct": False}
                ],
                "explanation": "Explanation of the correct answer",
                "dimension": dimension_name,
                "related_instances": [],
                "generation_timestamp": datetime.now().isoformat(),
                "generation_method": f"{self.llm_provider}_api",
                "qa_id": str(uuid.uuid4()),
                "error": str(e)
            }
    
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
            # Create Q&A directory
            # If output_dir already ends with "qa", don't add another "qa" subdirectory
            if output_dir.name == "qa":
                qa_dir = output_dir / dimension_name
            else:
                qa_dir = output_dir / "qa" / dimension_name
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
