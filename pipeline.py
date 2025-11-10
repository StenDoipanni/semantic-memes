"""
Main Pipeline Orchestrator.

This module provides the main pipeline class that orchestrates the entire
meme analysis process, from dimension extraction to Q&A generation and output formatting.
"""

import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from ontology_loader import OntologyLoader
from llm_integration import LLMManager
from dimensions_extractor import DimensionsExtractor
from qa_generator import QAGenerator
from jsonld_handler import JSONLDHandler
from config import (
    PipelineConfig, 
    QAConfig, 
    ErrorMessages, 
    SuccessMessages
)

logger = logging.getLogger(__name__)


class MemeAnalysisPipeline:
    """
    Main pipeline for meme analysis.
    
    This class orchestrates the complete meme analysis process:
    1. Load ontology and initialize components
    2. Extract dimensions from meme images
    3. Generate Q&A pairs based on extracted dimensions
    4. Create and save output files in various formats
    """
    
    def __init__(
        self,
        ontology_path: Optional[Path] = None,
        llm_provider: Optional[str] = None,
        output_dir: Optional[Path] = None
    ):
        """
        Initialize the meme analysis pipeline.
        
        Args:
            ontology_path: Path to the ontology file. If None, uses default.
            llm_provider: Preferred LLM provider ("claude" or "huggingface"). If None, auto-selects.
            output_dir: Output directory for results. If None, uses default.
        """
        self.ontology_path = ontology_path
        self.llm_provider = llm_provider
        self.output_dir = output_dir or PipelineConfig.OUTPUT_DIR
        
        # Initialize components
        self._initialize_components()
        
        logger.info("Meme analysis pipeline initialized")
    
    def _initialize_components(self) -> None:
        """Initialize all pipeline components."""
        try:
            # Initialize ontology loader
            self.ontology_loader = OntologyLoader(self.ontology_path)
            
            # Initialize LLM manager
            self.llm_manager = LLMManager()
            
            # Initialize JSON-LD handler
            self.jsonld_handler = JSONLDHandler()
            
            # Initialize dimensions extractor
            self.dimensions_extractor = DimensionsExtractor(
                self.ontology_loader,
                self.llm_manager,
                self.jsonld_handler
            )
            
            # Initialize Q&A generator
            self.qa_generator = QAGenerator(
                self.llm_manager,
                self.jsonld_handler
            )
            
            logger.info("All pipeline components initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize pipeline components: {e}")
            raise
    
    def analyze_meme(
        self,
        image_path: Path,
        selected_dimensions: Optional[List[str]] = None,
        question_types: Optional[List[str]] = None,
        questions_per_type: Optional[int] = None,
        save_outputs: bool = True
    ) -> Dict[str, Any]:
        """
        Analyze a meme image through the complete pipeline.
        
        Args:
            image_path: Path to the meme image
            selected_dimensions: List of dimension classes to extract
            question_types: Types of questions to generate
            questions_per_type: Number of questions per type
            save_outputs: Whether to save output files
            
        Returns:
            Complete analysis results dictionary
        """
        try:
            # Validate input
            self._validate_image_path(image_path)
            
            logger.info(f"Starting meme analysis for: {image_path}")
            
            # Create analysis metadata
            analysis_metadata = {
                "image_path": str(image_path),
                "image_name": image_path.name,
                "analysis_timestamp": datetime.now().isoformat(),
                "pipeline_version": "1.0.0",
                "llm_provider": self.llm_provider,
                "selected_dimensions": selected_dimensions,
                "question_types": question_types,
                "questions_per_type": questions_per_type
            }
            
            # Step 1: Extract dimensions
            logger.info("Step 1: Extracting dimensions...")
            dimensions_result = self.dimensions_extractor.extract_dimensions(
                image_path, 
                selected_dimensions, 
                self.llm_provider
            )
            
            if not dimensions_result["success"]:
                return {
                    "success": False,
                    "error": "Dimension extraction failed",
                    "details": dimensions_result["metadata"],
                    "metadata": analysis_metadata
                }
            
            # Step 2: Generate Q&A pairs
            logger.info("Step 2: Generating Q&A pairs...")
            qa_result = self.qa_generator.generate_qa_pairs(
                image_path,
                dimensions_result["dimensions"],
                question_types,
                questions_per_type,
                self.llm_provider
            )
            
            if not qa_result["success"]:
                logger.warning("Q&A generation failed, continuing with dimensions only")
            
            # Step 3: Create unified output
            logger.info("Step 3: Creating unified output...")
            unified_result = self._create_unified_output(
                dimensions_result,
                qa_result,
                image_path,
                analysis_metadata
            )
            
            # Step 4: Save outputs if requested
            saved_files = {}
            if save_outputs:
                logger.info("Step 4: Saving output files...")
                saved_files = self._save_all_outputs(
                    dimensions_result,
                    qa_result,
                    unified_result,
                    image_path
                )
            
            # Create final result
            final_result = {
                "success": True,
                "metadata": analysis_metadata,
                "dimensions": dimensions_result,
                "qa_generation": qa_result,
                "unified_output": unified_result,
                "saved_files": saved_files,
                "summary": self._create_analysis_summary(
                    dimensions_result,
                    qa_result,
                    saved_files
                )
            }
            
            logger.info(SuccessMessages.PIPELINE_COMPLETED)
            return final_result
            
        except Exception as e:
            error_msg = f"Pipeline analysis failed: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "metadata": {
                    "image_path": str(image_path),
                    "analysis_timestamp": datetime.now().isoformat()
                }
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
    
    def _create_unified_output(
        self,
        dimensions_result: Dict[str, Any],
        qa_result: Dict[str, Any],
        image_path: Path,
        analysis_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create unified output combining all analysis results.
        
        Args:
            dimensions_result: Dimensions extraction results
            qa_result: Q&A generation results
            image_path: Path to the analyzed image
            analysis_metadata: Analysis metadata
            
        Returns:
            Unified output dictionary
        """
        try:
            # Create unified JSON-LD document
            unified_jsonld = self.jsonld_handler.create_unified_jsonld(
                dimensions_result["dimensions"],
                qa_result.get("qa_pairs", []),
                image_path,
                metadata=analysis_metadata
            )
            
            # Create summary statistics
            summary_stats = {
                "total_dimensions": len(dimensions_result["dimensions"]),
                "total_qa_pairs": len(qa_result.get("qa_pairs", [])),
                "dimension_classes_used": len(set(
                    dim["class_name"] for dim in dimensions_result["dimensions"]
                )),
                "question_types_used": list(set(
                    qa["question_type"] for qa in qa_result.get("qa_pairs", [])
                )),
                "analysis_success_rate": 1.0 if dimensions_result["success"] else 0.0,
                "qa_success_rate": 1.0 if qa_result["success"] else 0.0
            }
            
            return {
                "unified_jsonld": unified_jsonld,
                "summary_stats": summary_stats,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Failed to create unified output: {e}")
            return {
                "unified_jsonld": None,
                "summary_stats": {},
                "success": False,
                "error": str(e)
            }
    
    def _save_all_outputs(
        self,
        dimensions_result: Dict[str, Any],
        qa_result: Dict[str, Any],
        unified_result: Dict[str, Any],
        image_path: Path
    ) -> Dict[str, Path]:
        """
        Save all output files.
        
        Args:
            dimensions_result: Dimensions extraction results
            qa_result: Q&A generation results
            unified_result: Unified output results
            image_path: Path to the analyzed image
            
        Returns:
            Dictionary mapping file types to saved file paths
        """
        saved_files = {}
        base_name = image_path.stem
        
        try:
            # Create output directories
            dimensions_dir = self.output_dir / "dimensions"
            qa_dir = self.output_dir / "qa"
            unified_dir = self.output_dir / "unified"
            
            for dir_path in [dimensions_dir, qa_dir, unified_dir]:
                dir_path.mkdir(parents=True, exist_ok=True)
            
            # Save dimensions outputs
            if dimensions_result["success"]:
                dim_files = self.dimensions_extractor.save_extraction_results(
                    dimensions_result, dimensions_dir, image_path
                )
                saved_files.update({f"dimensions_{k}": v for k, v in dim_files.items()})
            
            # Save Q&A outputs
            if qa_result["success"]:
                qa_files = self.qa_generator.save_qa_results(
                    qa_result, qa_dir, image_path
                )
                saved_files.update({f"qa_{k}": v for k, v in qa_files.items()})
            
            # Save unified output
            if unified_result["success"] and unified_result["unified_jsonld"]:
                unified_path = unified_dir / f"{base_name}_unified.jsonld"
                self.jsonld_handler.save_jsonld(
                    unified_result["unified_jsonld"], unified_path
                )
                saved_files["unified_jsonld"] = unified_path
                
                # Save summary statistics
                summary_path = unified_dir / f"{base_name}_summary.json"
                import json
                with open(summary_path, 'w', encoding='utf-8') as f:
                    json.dump(unified_result["summary_stats"], f, indent=2, ensure_ascii=False)
                saved_files["summary_stats"] = summary_path
            
            logger.info(f"Saved {len(saved_files)} output files")
            return saved_files
            
        except Exception as e:
            logger.error(f"Failed to save outputs: {e}")
            return {}
    
    def _create_analysis_summary(
        self,
        dimensions_result: Dict[str, Any],
        qa_result: Dict[str, Any],
        saved_files: Dict[str, Path]
    ) -> Dict[str, Any]:
        """
        Create a summary of the analysis results.
        
        Args:
            dimensions_result: Dimensions extraction results
            qa_result: Q&A generation results
            saved_files: Dictionary of saved files
            
        Returns:
            Analysis summary dictionary
        """
        return {
            "dimensions_extracted": len(dimensions_result.get("dimensions", [])),
            "qa_pairs_generated": len(qa_result.get("qa_pairs", [])),
            "files_saved": len(saved_files),
            "dimension_extraction_success": dimensions_result["success"],
            "qa_generation_success": qa_result["success"],
            "overall_success": dimensions_result["success"] and qa_result["success"],
            "output_files": list(saved_files.keys())
        }
    
    def batch_analyze(
        self,
        image_paths: List[Path],
        selected_dimensions: Optional[List[str]] = None,
        question_types: Optional[List[str]] = None,
        questions_per_type: Optional[int] = None,
        save_outputs: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Analyze multiple meme images in batch.
        
        Args:
            image_paths: List of paths to meme images
            selected_dimensions: List of dimension classes to extract
            question_types: Types of questions to generate
            questions_per_type: Number of questions per type
            save_outputs: Whether to save output files
            
        Returns:
            List of analysis results for each image
        """
        results = []
        
        logger.info(f"Starting batch analysis of {len(image_paths)} images")
        
        for i, image_path in enumerate(image_paths, 1):
            logger.info(f"Processing image {i}/{len(image_paths)}: {image_path}")
            
            try:
                result = self.analyze_meme(
                    image_path,
                    selected_dimensions,
                    question_types,
                    questions_per_type,
                    save_outputs
                )
                results.append(result)
                
            except Exception as e:
                logger.error(f"Failed to analyze {image_path}: {e}")
                results.append({
                    "success": False,
                    "error": str(e),
                    "image_path": str(image_path)
                })
        
        # Create batch summary
        successful_analyses = sum(1 for r in results if r["success"])
        logger.info(f"Batch analysis completed: {successful_analyses}/{len(image_paths)} successful")
        
        return results
    
    def get_pipeline_status(self) -> Dict[str, Any]:
        """
        Get the current status of the pipeline components.
        
        Returns:
            Pipeline status dictionary
        """
        return {
            "ontology_loaded": self.ontology_loader is not None,
            "llm_providers_available": self.llm_manager.get_available_providers(),
            "preferred_llm_provider": self.llm_provider,
            "output_directory": str(self.output_dir),
            "dimension_classes_available": len(self.dimensions_extractor.dimension_classes),
            "question_types_available": QAConfig.QUESTION_TYPES,
            "pipeline_ready": all([
                self.ontology_loader is not None,
                len(self.llm_manager.get_available_providers()) > 0,
                len(self.dimensions_extractor.dimension_classes) > 0
            ])
        }


# Convenience functions
def analyze_meme(
    image_path: Path,
    selected_dimensions: Optional[List[str]] = None,
    question_types: Optional[List[str]] = None,
    questions_per_type: Optional[int] = None,
    llm_provider: Optional[str] = None,
    output_dir: Optional[Path] = None,
    save_outputs: bool = True
) -> Dict[str, Any]:
    """
    Analyze a single meme image.
    
    Args:
        image_path: Path to the meme image
        selected_dimensions: List of dimension classes to extract
        question_types: Types of questions to generate
        questions_per_type: Number of questions per type
        llm_provider: LLM provider to use
        output_dir: Output directory for results
        save_outputs: Whether to save output files
        
    Returns:
        Analysis results dictionary
    """
    pipeline = MemeAnalysisPipeline(
        llm_provider=llm_provider,
        output_dir=output_dir
    )
    
    return pipeline.analyze_meme(
        image_path,
        selected_dimensions,
        question_types,
        questions_per_type,
        save_outputs
    )


def batch_analyze_memes(
    image_paths: List[Path],
    selected_dimensions: Optional[List[str]] = None,
    question_types: Optional[List[str]] = None,
    questions_per_type: Optional[int] = None,
    llm_provider: Optional[str] = None,
    output_dir: Optional[Path] = None,
    save_outputs: bool = True
) -> List[Dict[str, Any]]:
    """
    Analyze multiple meme images in batch.
    
    Args:
        image_paths: List of paths to meme images
        selected_dimensions: List of dimension classes to extract
        question_types: Types of questions to generate
        questions_per_type: Number of questions per type
        llm_provider: LLM provider to use
        output_dir: Output directory for results
        save_outputs: Whether to save output files
        
    Returns:
        List of analysis results
    """
    pipeline = MemeAnalysisPipeline(
        llm_provider=llm_provider,
        output_dir=output_dir
    )
    
    return pipeline.batch_analyze(
        image_paths,
        selected_dimensions,
        question_types,
        questions_per_type,
        save_outputs
    )


if __name__ == "__main__":
    # Example usage and testing
    import logging
    logging.basicConfig(level=logging.INFO)
    
    try:
        # Test with the provided meme image
        image_path = Path("/Users/stefanodegiorgis/Downloads/dev_set_task3_labeled/9_image_batch_2.png")
        
        if image_path.exists():
            # Analyze the meme
            result = analyze_meme(
                image_path,
                selected_dimensions=["OverallIntent", "VisualMaterial", "TextualMaterial"],
                question_types=["descriptive", "interpretive"],
                questions_per_type=2,
                output_dir=Path("output/test_pipeline")
            )
            
            print(f"Analysis successful: {result['success']}")
            if result['success']:
                summary = result['summary']
                print(f"Dimensions extracted: {summary['dimensions_extracted']}")
                print(f"Q&A pairs generated: {summary['qa_pairs_generated']}")
                print(f"Files saved: {summary['files_saved']}")
                print(f"Output files: {summary['output_files']}")
        else:
            print(f"Test image not found: {image_path}")
            
    except Exception as e:
        print(f"Error: {e}")
