"""
Script to initialize the annotations Excel file with meme IDs for all annotators.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.data_loader import DataLoader
from utils.annotation_manager import AnnotationManager

def main():
    """Initialize annotations Excel file with meme IDs."""
    print("Initializing annotations Excel file...")
    
    # Initialize components
    data_loader = DataLoader()
    annotation_manager = AnnotationManager()
    
    # Get available memes
    available_memes = data_loader.get_available_memes()
    
    if not available_memes:
        print("No memes found. Please check the image directory.")
        return
    
    print(f"Found {len(available_memes)} memes")
    
    # Get first 100 memes (or all if less than 100)
    meme_ids = available_memes[:100]
    print(f"Initializing {len(meme_ids)} meme IDs for each annotator...")
    
    # Initialize meme IDs for each annotator
    for annotator in AnnotationManager.ANNOTATORS:
        annotation_manager.initialize_meme_ids_for_annotator(annotator, meme_ids)
        print(f"✓ Initialized meme IDs for {annotator}")
    
    print(f"\nAnnotations Excel file created at: {annotation_manager.excel_file}")
    print("Initialization complete!")

if __name__ == "__main__":
    main()

