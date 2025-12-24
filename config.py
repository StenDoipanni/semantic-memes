"""
Configuration settings for the Meme Analysis Pipeline.

This module contains all configuration constants, default values, and settings
used throughout the pipeline components.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional

# Base paths
BASE_DIR = Path(__file__).parent
PROJECT_ROOT = BASE_DIR  # Project root is where config.py is located

# Load from environment variables or use defaults
ONTOLOGY_PATH = Path(os.getenv("ONTOLOGY_PATH", PROJECT_ROOT / "memes-features" / "meme-dimensions.ttl"))
PROMPTS_DIR = Path(os.getenv("PROMPTS_DIR", PROJECT_ROOT / "memes-features" / "prompts" / "dimension-extraction-prompts"))

# Output directories
OUTPUT_DIR = BASE_DIR / "output"
DIMENSIONS_OUTPUT_DIR = OUTPUT_DIR / "dimensions"
QA_OUTPUT_DIR = OUTPUT_DIR / "qa"

# Create output directories if they don't exist
OUTPUT_DIR.mkdir(exist_ok=True)
DIMENSIONS_OUTPUT_DIR.mkdir(exist_ok=True)
QA_OUTPUT_DIR.mkdir(exist_ok=True)

# LLM Configuration
class LLMConfig:
    """Configuration for LLM integrations."""
    
    # Claude API settings
    CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
    CLAUDE_MODEL = "claude-sonnet-4-5-20250929" # "claude-haiku-4-5-20251001"
    CLAUDE_MAX_TOKENS = 4000
    CLAUDE_TEMPERATURE = 0.1
    CLAUDE_MAX_IMAGE_SIZE = (4096, 4096)  # Increased image size tolerance
    
    # HuggingFace/Transformers settings
    HUGGINGFACE_MODEL = os.getenv("HUGGINGFACE_MODEL", "Qwen/Qwen3-VL-8B-Instruct")  # Vision-language model
    HUGGINGFACE_DEVICE = os.getenv("HUGGINGFACE_DEVICE", None)  # "cuda", "cpu", or None for auto-detection
    HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN", os.getenv("HF_TOKEN"))  # HuggingFace API token for authenticated requests
    HUGGINGFACE_MAX_TOKENS = 4000
    HUGGINGFACE_TEMPERATURE = 0.1
    HUGGINGFACE_MAX_IMAGE_SIZE = (1024, 1024)  # Reasonable size for vision models
    
    # Common settings
    MAX_RETRIES = 3
    RETRY_DELAY = 1.0

# Ontology Configuration
class OntologyConfig:
    """Configuration for ontology processing."""
    
    # Load paths from environment variables
    ONTOLOGY_PATH = Path(os.getenv("ONTOLOGY_PATH", PROJECT_ROOT / "memes-features" / "meme-dimensions.ttl"))
    PROMPTS_DIR = Path(os.getenv("PROMPTS_DIR", PROJECT_ROOT / "memes-features" / "prompts" / "dimension-extraction-prompts-refined"))
    
    # Namespace prefixes
    NAMESPACES = {
        "owl": "http://www.w3.org/2002/07/owl#",
        "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
        "meme": "http://example.org/multimodal-taxonomy#"
    }
    
    # Dimension classes to extract (based on ontology analysis)
    DIMENSION_CLASSES = [
        "VisualMaterial",
        "TextualMaterial", 
        "Emotion",
        "ColorComposition",
        "Scene",
        "BackgroundKnowledge",
        "Metadata",
        "AnalogicalMapping",
        "OverallIntent",
        "SemioticProjection",
        "TargetCommunity",
        "TemplateStructure",
        "Toxicity"
    ]
    
    # Properties to extract from classes
    EXTRACTION_PROPERTIES = [
        "promptExtractionText",
        "prototypicalQuestions",
        "rdfs:comment",
        "rdfs:label"
    ]

# Pipeline Configuration
class PipelineConfig:
    """Configuration for the main pipeline."""
    
    # Image processing
    SUPPORTED_IMAGE_FORMATS = [".png", ".jpg", ".jpeg", ".webp"]
    MAX_IMAGE_SIZE = (2048, 2048)
    
    # Processing settings
    BATCH_SIZE = 1
    PARALLEL_PROCESSING = False
    
    # Output settings
    INCLUDE_ORIGINAL_ONTOLOGY = True
    GENERATE_TEXT_OUTPUT = True
    GENERATE_JSONLD_OUTPUT = True
    
    # Available dimension classes (from ontology)
    DIMENSION_CLASSES = [
        "VisualMaterial",
        "TextualMaterial", 
        "Emotion",
        "ColorComposition",
        "Scene",
        "BackgroundKnowledge",
        "Metadata",
        "AnalogicalMapping",
        "OverallIntent",
        "SemioticProjection",
        "TargetCommunity",
        "TemplateStructure",
        "Toxicity"
    ]

# Q&A Generation Configuration
class QAConfig:
    """Configuration for Q&A generation."""
    
    # Question types to generate
    QUESTION_TYPES = [
        "descriptive",
        "analytical", 
        "interpretive",
        "contextual",
        "evaluative"
    ]
    
    # Number of questions per type
    QUESTIONS_PER_TYPE = 2
    
    # Answer settings
    MIN_ANSWER_LENGTH = 50
    MAX_ANSWER_LENGTH = 500

# Logging Configuration
class LoggingConfig:
    """Configuration for logging."""
    
    LOG_LEVEL = "INFO"
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE = OUTPUT_DIR / "pipeline.log"

# Validation settings
class ValidationConfig:
    """Configuration for input/output validation."""
    
    # Required fields in dimension extraction output
    REQUIRED_DIMENSION_FIELDS = ["instance_name", "label", "description"]
    
    # Required fields in Q&A output
    REQUIRED_QA_FIELDS = ["question", "answer", "question_type"]
    
    # JSON-LD context
    JSONLD_CONTEXT = {
        "@vocab": "http://example.org/multimodal-taxonomy#",
        "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
        "owl": "http://www.w3.org/2002/07/owl#"
    }

# Error messages
class ErrorMessages:
    """Standard error messages used throughout the pipeline."""
    
    INVALID_IMAGE_FORMAT = "Unsupported image format. Supported formats: {formats}"
    IMAGE_NOT_FOUND = "Image file not found: {path}"
    ONTOLOGY_LOAD_ERROR = "Failed to load ontology: {error}"
    LLM_API_ERROR = "LLM API error: {error}"
    DIMENSION_EXTRACTION_ERROR = "Dimension extraction failed: {error}"
    QA_GENERATION_ERROR = "Q&A generation failed: {error}"
    JSONLD_SERIALIZATION_ERROR = "JSON-LD serialization failed: {error}"

# Success messages
class SuccessMessages:
    """Standard success messages used throughout the pipeline."""
    
    PIPELINE_COMPLETED = "Pipeline completed successfully"
    DIMENSIONS_EXTRACTED = "Dimensions extracted: {count} dimensions found"
    QA_GENERATED = "Q&A generated: {count} question-answer pairs"
    OUTPUT_SAVED = "Output saved to: {path}"
