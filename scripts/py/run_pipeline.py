#!/usr/bin/env python3
"""
Command-line interface for the Meme Analysis Pipeline.

This script provides a command-line interface for running the meme analysis
pipeline with various options and configurations.
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import List, Optional

# Ensure repository root (two levels up from scripts/py) is on sys.path
CURRENT_FILE = Path(__file__).resolve()
REPO_ROOT = CURRENT_FILE.parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from pipeline import MemeAnalysisPipeline, analyze_meme, batch_analyze_memes
from dimension_extraction_module import DimensionExtractionModule, extract_dimensions_from_image
from config import PipelineConfig, QAConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False, log_file: Optional[Path] = None):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # Create file handler if specified
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Meme Analysis Pipeline - Analyze memes using LLMs and ontological knowledge",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze a single meme (full pipeline)
  python run_pipeline.py /path/to/meme.png

  # Extract dimensions only
  python run_pipeline.py /path/to/meme.png --mode dimension_extraction

  # Analyze with specific dimensions
  python run_pipeline.py /path/to/meme.png --dimensions VisualMaterial TextualMaterial

  # Extract specific dimensions only
  python run_pipeline.py /path/to/meme.png --mode dimension_extraction --dimensions OverallIntent VisualMaterial

  # Analyze with specific question types
  python run_pipeline.py /path/to/meme.png --question-types descriptive interpretive

  # Batch analyze multiple memes
  python run_pipeline.py /path/to/memes/ --batch

  # Use specific LLM provider
  python run_pipeline.py /path/to/meme.png --llm-provider claude

  # Custom output directory
  python run_pipeline.py /path/to/meme.png --output-dir /path/to/output
        """
    )
    
    # Input arguments
    parser.add_argument(
        "input_path",
        type=Path,
        help="Path to meme image or directory containing meme images"
    )
    
    # Analysis options
    parser.add_argument(
        "--dimensions",
        nargs="*",
        choices=PipelineConfig.DIMENSION_CLASSES,
        help="Specific dimension classes to extract"
    )
    
    parser.add_argument(
        "--question-types",
        nargs="*",
        choices=QAConfig.QUESTION_TYPES,
        help="Types of questions to generate"
    )
    
    parser.add_argument(
        "--questions-per-type",
        type=int,
        default=QAConfig.QUESTIONS_PER_TYPE,
        help=f"Number of questions per type (default: {QAConfig.QUESTIONS_PER_TYPE})"
    )
    
    # LLM options
    parser.add_argument(
        "--llm-provider",
        choices=["claude", "huggingface"],
        help="Specific LLM provider to use (auto-select if not specified)"
    )
    
    # Output options
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Output directory for results (default: ./output)"
    )
    
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Don't save output files"
    )
    
    # Batch processing
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Process multiple images in batch mode"
    )
    
    # Logging options
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    parser.add_argument(
        "--log-file",
        type=Path,
        help="Log file path"
    )
    
    # Pipeline options
    parser.add_argument(
        "--ontology-path",
        type=Path,
        help="Path to custom ontology file"
    )
    
    # Pipeline mode
    parser.add_argument(
        "--mode",
        choices=["full", "dimension_extraction"],
        default="full",
        help="Pipeline mode: 'full' for complete analysis, 'dimension_extraction' for dimensions only"
    )
    
    return parser.parse_args()


def validate_input_path(input_path: Path, batch_mode: bool) -> List[Path]:
    """
    Validate input path and return list of valid image paths.
    
    Args:
        input_path: Input path (file or directory)
        batch_mode: Whether to process in batch mode
        
    Returns:
        List of valid image paths
        
    Raises:
        SystemExit: If no valid images found
    """
    valid_paths = []
    
    if input_path.is_file():
        if batch_mode:
            logger.error("Batch mode specified but input is a single file")
            sys.exit(1)
        
        if input_path.suffix.lower() in PipelineConfig.SUPPORTED_IMAGE_FORMATS:
            valid_paths.append(input_path)
        else:
            logger.error(f"Unsupported image format: {input_path.suffix}")
            sys.exit(1)
    
    elif input_path.is_dir():
        if not batch_mode:
            logger.error("Directory specified but batch mode not enabled")
            sys.exit(1)
        
        # Find all valid image files in directory
        for ext in PipelineConfig.SUPPORTED_IMAGE_FORMATS:
            valid_paths.extend(input_path.glob(f"*{ext}"))
            valid_paths.extend(input_path.glob(f"*{ext.upper()}"))
        
        if not valid_paths:
            logger.error(f"No valid image files found in directory: {input_path}")
            sys.exit(1)
    
    else:
        logger.error(f"Input path does not exist: {input_path}")
        sys.exit(1)
    
    return valid_paths


def run_single_analysis(args) -> None:
    """Run analysis for a single image."""
    image_path = args.input_path
    
    logger.info(f"Analyzing single image: {image_path}")
    
    try:
        if args.mode == "dimension_extraction":
            # Use dimension extraction module
            result = extract_dimensions_from_image(
                image_path=image_path,
                selected_dimensions=args.dimensions,
                output_dir=args.output_dir,
                llm_provider=args.llm_provider or "claude"
            )
        else:
            # Use full pipeline
            result = analyze_meme(
                image_path=image_path,
                selected_dimensions=args.dimensions,
                question_types=args.question_types,
                questions_per_type=args.questions_per_type,
                llm_provider=args.llm_provider,
                output_dir=args.output_dir,
                save_outputs=not args.no_save
            )
        
        # Print results
        if result['success']:
            if args.mode == "dimension_extraction":
                print(f"\n✅ Dimension extraction completed successfully!")
                print(f"📊 Dimensions extracted: {result['metadata']['total_dimensions_found']}")
                print(f"🔍 Dimensions processed: {', '.join(result['metadata']['dimensions_processed'])}")
                
                if result.get('saved_files'):
                    print(f"\n📁 Output files:")
                    for file_type, file_path in result['saved_files'].items():
                        if isinstance(file_path, list):
                            if file_type.endswith("_individual"):
                                dimension_name = file_type.replace("_individual", "")
                                print(f"  - {file_type}: {len(file_path)} files in dimensions/{dimension_name}/")
                                for fp in file_path[:2]:  # Show first 2 files
                                    print(f"    • {fp}")
                                if len(file_path) > 2:
                                    print(f"    • ... and {len(file_path) - 2} more")
                            else:
                                print(f"  - {file_type}: {len(file_path)} files")
                                for fp in file_path[:3]:  # Show first 3 files
                                    print(f"    • {fp}")
                                if len(file_path) > 3:
                                    print(f"    • ... and {len(file_path) - 3} more")
                        else:
                            print(f"  - {file_type}: {file_path}")
            else:
                summary = result['summary']
                print(f"\n✅ Analysis completed successfully!")
                print(f"📊 Dimensions extracted: {summary['dimensions_extracted']}")
                print(f"❓ Q&A pairs generated: {summary['qa_pairs_generated']}")
                print(f"💾 Files saved: {summary['files_saved']}")
                
                if not args.no_save and result.get('saved_files'):
                    print(f"\n📁 Output files:")
                    for file_type, file_path in result['saved_files'].items():
                        print(f"  - {file_type}: {file_path}")
        else:
            print(f"\n❌ Analysis failed: {result.get('error', 'Unknown error')}")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        print(f"\n❌ Analysis failed: {e}")
        sys.exit(1)


def run_batch_analysis(args) -> None:
    """Run batch analysis for multiple images."""
    image_paths = validate_input_path(args.input_path, batch_mode=True)
    
    logger.info(f"Analyzing {len(image_paths)} images in batch mode")
    
    try:
        results = batch_analyze_memes(
            image_paths=image_paths,
            selected_dimensions=args.dimensions,
            question_types=args.question_types,
            questions_per_type=args.questions_per_type,
            llm_provider=args.llm_provider,
            output_dir=args.output_dir,
            save_outputs=not args.no_save
        )
        
        # Print batch results
        successful = sum(1 for r in results if r['success'])
        failed = len(results) - successful
        
        print(f"\n📊 Batch analysis completed!")
        print(f"✅ Successful: {successful}")
        print(f"❌ Failed: {failed}")
        
        if failed > 0:
            print(f"\n❌ Failed analyses:")
            for i, result in enumerate(results):
                if not result['success']:
                    print(f"  - {result.get('image_path', f'Image {i+1}')}: {result.get('error', 'Unknown error')}")
        
        if successful > 0:
            print(f"\n✅ Successful analyses:")
            for i, result in enumerate(results):
                if result['success']:
                    summary = result['summary']
                    image_name = Path(result['metadata']['image_name']).name
                    print(f"  - {image_name}: {summary['dimensions_extracted']} dimensions, "
                          f"{summary['qa_pairs_generated']} Q&A pairs")
        
        if failed > 0:
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Batch analysis failed: {e}")
        print(f"\n❌ Batch analysis failed: {e}")
        sys.exit(1)


def main():
    """Main entry point."""
    args = parse_arguments()
    
    # Setup logging
    setup_logging(verbose=args.verbose, log_file=args.log_file)
    
    # Validate input
    if args.batch:
        validate_input_path(args.input_path, batch_mode=True)
    else:
        validate_input_path(args.input_path, batch_mode=False)
    
    # Print configuration
    print("🚀 Meme Analysis Pipeline")
    print("=" * 50)
    print(f"📁 Input: {args.input_path}")
    print(f"🔧 Mode: {args.mode}")
    print(f"🤖 LLM Provider: {args.llm_provider or 'Auto-select'}")
    print(f"📊 Dimensions: {args.dimensions or 'All available'}")
    if args.mode == "full":
        print(f"❓ Question Types: {args.question_types or 'All available'}")
        print(f"🔢 Questions per Type: {args.questions_per_type}")
    print(f"💾 Save Outputs: {not args.no_save}")
    if args.output_dir:
        print(f"📁 Output Directory: {args.output_dir}")
    print("=" * 50)
    
    # Run analysis
    if args.batch:
        run_batch_analysis(args)
    else:
        run_single_analysis(args)


if __name__ == "__main__":
    main()
