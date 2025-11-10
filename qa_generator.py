"""
Q&A Generation Component.

This module implements the functionality for generating questions and answers
about memes based on extracted dimensions. It uses LLMs to create meaningful
Q&A pairs that explore different aspects of the meme.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import re

from llm_integration import LLMManager
from jsonld_handler import JSONLDHandler
from config import (
    QAConfig, 
    PipelineConfig, 
    ErrorMessages, 
    SuccessMessages
)

logger = logging.getLogger(__name__)


class QAGenerator:
    """
    Component for generating questions and answers about memes.
    
    This class uses extracted dimensions and LLMs to generate meaningful
    Q&A pairs that explore different aspects of the meme content.
    """
    
    def __init__(
        self, 
        llm_manager: Optional[LLMManager] = None,
        jsonld_handler: Optional[JSONLDHandler] = None
    ):
        """
        Initialize the Q&A generator.
        
        Args:
            llm_manager: LLM manager instance. If None, creates new one.
            jsonld_handler: JSON-LD handler instance. If None, creates new one.
        """
        self.llm_manager = llm_manager or LLMManager()
        self.jsonld_handler = jsonld_handler or JSONLDHandler()
        
        # Q&A generation templates
        self.qa_templates = self._load_qa_templates()
        
        logger.info("Q&A generator initialized")
    
    def generate_qa_pairs(
        self, 
        image_path: Path,
        dimensions_data: List[Dict[str, Any]],
        question_types: Optional[List[str]] = None,
        questions_per_type: Optional[int] = None,
        llm_provider: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate Q&A pairs for a meme based on extracted dimensions.
        
        Args:
            image_path: Path to the meme image
            dimensions_data: List of extracted dimensions
            question_types: Types of questions to generate. If None, uses all types.
            questions_per_type: Number of questions per type. If None, uses default.
            llm_provider: Specific LLM provider to use
            
        Returns:
            Dictionary containing generated Q&A pairs and metadata
        """
        try:
            # Validate input
            self._validate_inputs(image_path, dimensions_data)
            
            # Set defaults
            question_types = question_types or QAConfig.QUESTION_TYPES
            questions_per_type = questions_per_type or QAConfig.QUESTIONS_PER_TYPE
            
            logger.info(f"Generating Q&A pairs for: {image_path}")
            logger.info(f"Question types: {question_types}")
            logger.info(f"Questions per type: {questions_per_type}")
            
            # Generate Q&A pairs
            qa_pairs = []
            generation_metadata = {
                "image_path": str(image_path),
                "image_name": image_path.name,
                "generation_timestamp": None,
                "llm_provider": None,
                "question_types_processed": [],
                "total_qa_pairs": 0,
                "dimensions_used": len(dimensions_data)
            }
            
            for question_type in question_types:
                try:
                    type_qa_pairs = self._generate_questions_for_type(
                        image_path, 
                        dimensions_data, 
                        question_type, 
                        questions_per_type,
                        llm_provider
                    )
                    
                    if type_qa_pairs:
                        qa_pairs.extend(type_qa_pairs)
                        generation_metadata["question_types_processed"].append(question_type)
                        logger.debug(f"Generated {len(type_qa_pairs)} Q&A pairs for type: {question_type}")
                    
                except Exception as e:
                    logger.warning(f"Failed to generate Q&A for type {question_type}: {e}")
                    continue
            
            # Update metadata
            generation_metadata["generation_timestamp"] = self._get_timestamp()
            generation_metadata["total_qa_pairs"] = len(qa_pairs)
            
            # Create result
            result = {
                "qa_pairs": qa_pairs,
                "metadata": generation_metadata,
                "success": True
            }
            
            logger.info(SuccessMessages.QA_GENERATED.format(count=len(qa_pairs)))
            return result
            
        except Exception as e:
            error_msg = ErrorMessages.QA_GENERATION_ERROR.format(error=str(e))
            logger.error(error_msg)
            return {
                "qa_pairs": [],
                "metadata": {"error": error_msg},
                "success": False
            }
    
    def _validate_inputs(self, image_path: Path, dimensions_data: List[Dict[str, Any]]) -> None:
        """
        Validate input parameters.
        
        Args:
            image_path: Path to validate
            dimensions_data: Dimensions data to validate
            
        Raises:
            ValueError: If inputs are invalid
        """
        if not image_path.exists():
            raise ValueError(ErrorMessages.IMAGE_NOT_FOUND.format(path=image_path))
        
        if not isinstance(dimensions_data, list):
            raise ValueError("Dimensions data must be a list")
        
        if not dimensions_data:
            raise ValueError("No dimensions data provided")
    
    def _generate_questions_for_type(
        self, 
        image_path: Path, 
        dimensions_data: List[Dict[str, Any]], 
        question_type: str,
        questions_per_type: int,
        llm_provider: Optional[str]
    ) -> List[Dict[str, Any]]:
        """
        Generate questions for a specific type.
        
        Args:
            image_path: Path to the image
            dimensions_data: Extracted dimensions
            question_type: Type of questions to generate
            questions_per_type: Number of questions to generate
            llm_provider: LLM provider to use
            
        Returns:
            List of generated Q&A pairs
        """
        # Get template for question type
        template = self.qa_templates.get(question_type)
        if not template:
            logger.warning(f"No template found for question type: {question_type}")
            return []
        
        # Create the generation prompt
        prompt = self._create_qa_generation_prompt(
            template, dimensions_data, question_type, questions_per_type
        )
        
        # Generate response using LLM
        try:
            response = self.llm_manager.generate_response(
                prompt, 
                image_path, 
                provider=llm_provider
            )
            
            # Parse the response
            qa_pairs = self._parse_qa_response(response, question_type)
            
            return qa_pairs
            
        except Exception as e:
            logger.error(f"LLM Q&A generation failed for type {question_type}: {e}")
            return []
    
    def _create_qa_generation_prompt(
        self, 
        template: Dict[str, Any], 
        dimensions_data: List[Dict[str, Any]], 
        question_type: str,
        questions_per_type: int
    ) -> str:
        """
        Create the Q&A generation prompt.
        
        Args:
            template: Q&A template for the question type
            dimensions_data: Extracted dimensions
            question_type: Type of questions
            questions_per_type: Number of questions to generate
            
        Returns:
            Complete generation prompt
        """
        # Format dimensions data for the prompt
        dimensions_text = self._format_dimensions_for_prompt(dimensions_data)
        
        # Create the full prompt
        prompt = f"""You are generating {question_type} questions and answers about a meme image.

Question Type: {question_type}
Description: {template.get('description', '')}
Instructions: {template.get('instructions', '')}

Extracted Dimensions:
{dimensions_text}

Please generate exactly {questions_per_type} {question_type} question-answer pairs about this meme. Each Q&A pair should:

1. Be directly related to the extracted dimensions
2. Explore different aspects of the meme
3. Be clear and specific
4. Have detailed, informative answers

Format your response as a JSON array with the following structure:
[
  {{
    "question": "Your question here",
    "answer": "Your detailed answer here",
    "question_type": "{question_type}",
    "related_dimensions": ["dimension1", "dimension2"]
  }}
]

Make sure the questions are insightful and the answers are comprehensive (at least {QAConfig.MIN_ANSWER_LENGTH} characters)."""

        return prompt
    
    def _format_dimensions_for_prompt(self, dimensions_data: List[Dict[str, Any]]) -> str:
        """
        Format dimensions data for use in prompts.
        
        Args:
            dimensions_data: List of dimension data
            
        Returns:
            Formatted dimensions text
        """
        formatted_text = ""
        
        for i, dim in enumerate(dimensions_data, 1):
            formatted_text += f"{i}. {dim['class_name']}: {dim['label']}\n"
            formatted_text += f"   Description: {dim['description']}\n"
            if 'confidence' in dim:
                formatted_text += f"   Confidence: {dim['confidence']}\n"
            formatted_text += "\n"
        
        return formatted_text
    
    def _parse_qa_response(self, response: str, question_type: str) -> List[Dict[str, Any]]:
        """
        Parse the LLM response to extract Q&A pairs.
        
        Args:
            response: Raw LLM response
            question_type: Type of questions generated
            
        Returns:
            List of parsed Q&A pairs
        """
        qa_pairs = []
        
        try:
            # Try to extract JSON from the response
            json_data = self._extract_json_from_response(response)
            
            if isinstance(json_data, list):
                # Multiple Q&A pairs
                for item in json_data:
                    qa_pair = self._create_qa_pair(item, question_type)
                    if qa_pair:
                        qa_pairs.append(qa_pair)
            elif isinstance(json_data, dict):
                # Single Q&A pair
                qa_pair = self._create_qa_pair(json_data, question_type)
                if qa_pair:
                    qa_pairs.append(qa_pair)
            
        except Exception as e:
            logger.warning(f"Failed to parse Q&A response for type {question_type}: {e}")
            # Try to extract Q&A pairs using regex as fallback
            qa_pairs = self._extract_qa_with_regex(response, question_type)
        
        return qa_pairs
    
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
            r'\[.*?\]',
            r'\{.*?\}'
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
    
    def _create_qa_pair(self, data: Dict[str, Any], question_type: str) -> Optional[Dict[str, Any]]:
        """
        Create a Q&A pair from parsed data.
        
        Args:
            data: Parsed Q&A data
            question_type: Type of the question
            
        Returns:
            Formatted Q&A pair or None if invalid
        """
        try:
            # Validate required fields
            required_fields = ["question", "answer"]
            if not all(field in data for field in required_fields):
                logger.warning(f"Missing required fields in Q&A data: {data}")
                return None
            
            # Validate answer length
            answer = data["answer"]
            if len(answer) < QAConfig.MIN_ANSWER_LENGTH:
                logger.warning(f"Answer too short: {len(answer)} characters")
                return None
            
            if len(answer) > QAConfig.MAX_ANSWER_LENGTH:
                answer = answer[:QAConfig.MAX_ANSWER_LENGTH] + "..."
            
            # Create the Q&A pair
            qa_pair = {
                "question": data["question"],
                "answer": answer,
                "question_type": data.get("question_type", question_type),
                "related_dimensions": data.get("related_dimensions", []),
                "confidence": data.get("confidence", 0.8),
                "generation_method": "llm_analysis"
            }
            
            return qa_pair
            
        except Exception as e:
            logger.error(f"Error creating Q&A pair: {e}")
            return None
    
    def _extract_qa_with_regex(
        self, 
        response: str, 
        question_type: str
    ) -> List[Dict[str, Any]]:
        """
        Extract Q&A pairs using regex patterns as fallback.
        
        Args:
            response: Raw LLM response
            question_type: Type of questions
            
        Returns:
            List of extracted Q&A pairs
        """
        qa_pairs = []
        
        # Simple regex patterns to extract Q&A information
        question_pattern = r'[Qq]uestion[:\s]*([^\n]+)'
        answer_pattern = r'[Aa]nswer[:\s]*([^\n]+(?:\n(?!Question)[^\n]*)*)'
        
        questions = re.findall(question_pattern, response, re.IGNORECASE)
        answers = re.findall(answer_pattern, response, re.IGNORECASE | re.DOTALL)
        
        # Create Q&A pairs from extracted data
        max_pairs = min(len(questions), len(answers))
        
        for i in range(max_pairs):
            try:
                question = questions[i].strip()
                answer = answers[i].strip()
                
                # Validate answer length
                if len(answer) < QAConfig.MIN_ANSWER_LENGTH:
                    continue
                
                if len(answer) > QAConfig.MAX_ANSWER_LENGTH:
                    answer = answer[:QAConfig.MAX_ANSWER_LENGTH] + "..."
                
                qa_pair = {
                    "question": question,
                    "answer": answer,
                    "question_type": question_type,
                    "related_dimensions": [],
                    "confidence": 0.5,
                    "generation_method": "regex_fallback"
                }
                qa_pairs.append(qa_pair)
                
            except Exception as e:
                logger.warning(f"Error creating fallback Q&A pair {i}: {e}")
                continue
        
        return qa_pairs
    
    def _load_qa_templates(self) -> Dict[str, Dict[str, str]]:
        """
        Load Q&A generation templates for different question types.
        
        Returns:
            Dictionary of question type templates
        """
        templates = {
            "descriptive": {
                "description": "Questions that ask for factual descriptions of what is visible in the meme",
                "instructions": "Focus on observable elements, visual details, and literal content"
            },
            "analytical": {
                "description": "Questions that require analysis of relationships, patterns, or structures",
                "instructions": "Focus on how elements relate to each other, compositional analysis, and structural patterns"
            },
            "interpretive": {
                "description": "Questions that ask for interpretation of meaning, symbolism, or implications",
                "instructions": "Focus on symbolic meaning, cultural references, and implied messages"
            },
            "contextual": {
                "description": "Questions that explore background knowledge, cultural context, or references",
                "instructions": "Focus on cultural knowledge, historical context, and background information needed to understand the meme"
            },
            "evaluative": {
                "description": "Questions that ask for evaluation, judgment, or assessment of the meme",
                "instructions": "Focus on effectiveness, impact, quality, or appropriateness of the meme"
            }
        }
        
        return templates
    
    def _get_timestamp(self) -> str:
        """Get current timestamp as ISO string."""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def save_qa_results(
        self, 
        results: Dict[str, Any], 
        output_dir: Path,
        image_path: Path
    ) -> Dict[str, Path]:
        """
        Save Q&A generation results to files.
        
        Args:
            results: Q&A generation results
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
            if results["success"] and results["qa_pairs"]:
                jsonld_doc = self.jsonld_handler.create_qa_jsonld(
                    results["qa_pairs"], 
                    image_path, 
                    metadata=results["metadata"]
                )
                
                jsonld_path = output_dir / f"{base_name}_qa.jsonld"
                self.jsonld_handler.save_jsonld(jsonld_doc, jsonld_path)
                saved_files["qa_jsonld"] = jsonld_path
                
                # Save raw JSON for debugging
                raw_json_path = output_dir / f"{base_name}_qa_raw.json"
                with open(raw_json_path, 'w', encoding='utf-8') as f:
                    json.dump(results, f, indent=2, ensure_ascii=False)
                saved_files["raw_json"] = raw_json_path
            
            # Save text file
            text_path = output_dir / f"{base_name}_qa.txt"
            self._save_qa_text(results, text_path)
            saved_files["text_file"] = text_path
            
            logger.info(f"Q&A results saved to: {output_dir}")
            return saved_files
            
        except Exception as e:
            logger.error(f"Failed to save Q&A results: {e}")
            return {}
    
    def _save_qa_text(self, results: Dict[str, Any], output_path: Path) -> None:
        """
        Save Q&A results as a text file.
        
        Args:
            results: Q&A generation results
            output_path: Path to save the text file
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"Questions and Answers\n")
            f.write(f"====================\n\n")
            
            if results["success"]:
                f.write(f"Image: {results['metadata']['image_name']}\n")
                f.write(f"Generation Time: {results['metadata']['generation_timestamp']}\n")
                f.write(f"LLM Provider: {results['metadata'].get('llm_provider', 'Unknown')}\n")
                f.write(f"Total Q&A Pairs: {results['metadata']['total_qa_pairs']}\n")
                f.write(f"Dimensions Used: {results['metadata']['dimensions_used']}\n\n")
                
                f.write("Generated Questions and Answers:\n")
                f.write("==============================\n\n")
                
                for i, qa in enumerate(results["qa_pairs"], 1):
                    f.write(f"{i}. [{qa['question_type'].upper()}] {qa['question']}\n")
                    f.write(f"   Answer: {qa['answer']}\n")
                    if qa.get('related_dimensions'):
                        f.write(f"   Related Dimensions: {', '.join(qa['related_dimensions'])}\n")
                    f.write(f"   Confidence: {qa.get('confidence', 'N/A')}\n\n")
            else:
                f.write(f"Q&A generation failed: {results['metadata'].get('error', 'Unknown error')}\n")


# Convenience functions
def generate_qa_for_image(
    image_path: Path,
    dimensions_data: List[Dict[str, Any]],
    question_types: Optional[List[str]] = None,
    questions_per_type: Optional[int] = None,
    llm_provider: Optional[str] = None,
    output_dir: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Generate Q&A pairs for a meme image.
    
    Args:
        image_path: Path to the meme image
        dimensions_data: Extracted dimensions data
        question_types: Types of questions to generate
        questions_per_type: Number of questions per type
        llm_provider: LLM provider to use
        output_dir: Directory to save results
        
    Returns:
        Q&A generation results dictionary
    """
    generator = QAGenerator()
    results = generator.generate_qa_pairs(
        image_path, dimensions_data, question_types, questions_per_type, llm_provider
    )
    
    if output_dir and results["success"]:
        saved_files = generator.save_qa_results(results, output_dir, image_path)
        results["saved_files"] = saved_files
    
    return results


if __name__ == "__main__":
    # Example usage and testing
    import logging
    logging.basicConfig(level=logging.INFO)
    
    try:
        # Test with sample dimensions data
        test_dimensions = [
            {
                "class_name": "VisualMaterial",
                "instance_name": "smiling_girl",
                "label": "the smiling girl",
                "description": "A young girl with a mischievous smile in the foreground"
            },
            {
                "class_name": "OverallIntent",
                "instance_name": "humor_intent",
                "label": "the humor intent",
                "description": "The meme appears designed to create humor through contrast"
            }
        ]
        
        image_path = Path("/Users/stefanodegiorgis/Downloads/dev_set_task3_labeled/9_image_batch_2.png")
        
        if image_path.exists():
            # Generate Q&A pairs
            results = generate_qa_for_image(
                image_path,
                test_dimensions,
                question_types=["descriptive", "interpretive"],
                questions_per_type=2,
                output_dir=Path("output/test_qa")
            )
            
            print(f"Q&A generation successful: {results['success']}")
            print(f"Q&A pairs generated: {len(results['qa_pairs'])}")
            
            if results["success"]:
                for qa in results["qa_pairs"]:
                    print(f"- [{qa['question_type']}] {qa['question']}")
        else:
            print(f"Test image not found: {image_path}")
            
    except Exception as e:
        print(f"Error: {e}")
