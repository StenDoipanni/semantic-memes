"""
Annotation manager for saving and loading user annotations in Excel format with multiple sheets.
"""

from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime
import logging
import pandas as pd

logger = logging.getLogger(__name__)


class AnnotationManager:
    """Manages user annotations for meme dimensions in Excel format with multiple sheets."""
    
    # Available annotators
    ANNOTATORS = ["Stefano", "TC", "Lucia"]
    
    def __init__(self, annotations_dir: Optional[Path] = None, excel_file: Optional[Path] = None):
        """
        Initialize the annotation manager.
        
        Args:
            annotations_dir: Directory to store annotations. Defaults to memes-annotation/annotations/
            excel_file: Path to Excel file. Defaults to annotations_dir/annotations.xlsx
        """
        if annotations_dir is None:
            annotations_dir = Path(__file__).parent.parent / "annotations"
        
        self.annotations_dir = Path(annotations_dir)
        self.annotations_dir.mkdir(exist_ok=True)
        
        # Excel file for tabular storage
        self.excel_file = excel_file or (self.annotations_dir / "annotations.xlsx")
        self._initialize_excel()
    
    def _initialize_excel(self):
        """Initialize Excel file with sheets for each annotator if it doesn't exist."""
        if not self.excel_file.exists():
            # Create Excel file with one sheet per annotator
            with pd.ExcelWriter(self.excel_file, engine='openpyxl') as writer:
                for annotator in self.ANNOTATORS:
                    # Create empty DataFrame with required columns
                    df = pd.DataFrame(columns=['memeID', 'annotation', 'date', 'knowledge'])
                    df.to_excel(writer, sheet_name=annotator, index=False)
            
            logger.info(f"Created new Excel file: {self.excel_file}")
    
    def get_annotator_sheet(self, annotator: str) -> pd.DataFrame:
        """
        Get the DataFrame for a specific annotator's sheet.
        
        Args:
            annotator: Name of the annotator
            
        Returns:
            DataFrame for the annotator's sheet
        """
        if annotator not in self.ANNOTATORS:
            raise ValueError(f"Unknown annotator: {annotator}. Available: {self.ANNOTATORS}")
        
        try:
            df = pd.read_excel(self.excel_file, sheet_name=annotator)
            # Ensure all required columns exist with correct dtype
            for col in ['memeID', 'annotation', 'date', 'knowledge']:
                if col not in df.columns:
                    df[col] = None
                # Convert to object dtype to avoid dtype warnings when setting string values
                df[col] = df[col].astype('object')
            # Remove rows where memeID is NaN (empty rows)
            df = df.dropna(subset=['memeID'])
            return df
        except Exception as e:
            logger.error(f"Error reading sheet for {annotator}: {e}")
            # Return empty DataFrame with correct columns
            return pd.DataFrame(columns=['memeID', 'annotation', 'date', 'knowledge'])
    
    def save_annotator_sheet(self, annotator: str, df: pd.DataFrame):
        """
        Save the DataFrame back to the annotator's sheet.
        
        Args:
            annotator: Name of the annotator
            df: DataFrame to save
        """
        if annotator not in self.ANNOTATORS:
            raise ValueError(f"Unknown annotator: {annotator}. Available: {self.ANNOTATORS}")
        
        try:
            # Read all sheets
            all_sheets = {}
            for ann in self.ANNOTATORS:
                if ann == annotator:
                    all_sheets[ann] = df
                else:
                    all_sheets[ann] = self.get_annotator_sheet(ann)
            
            # Write all sheets back
            with pd.ExcelWriter(self.excel_file, engine='openpyxl') as writer:
                for ann, sheet_df in all_sheets.items():
                    sheet_df.to_excel(writer, sheet_name=ann, index=False)
            
            logger.info(f"Saved annotations for {annotator}")
        except Exception as e:
            logger.error(f"Error saving sheet for {annotator}: {e}")
            raise
    
    def save_annotation(self, annotator: str, meme_id: str, annotation: str, knowledge: str = ""):
        """
        Save an annotation for a specific meme.
        
        Args:
            annotator: Name of the annotator
            meme_id: ID of the meme (filename)
            annotation: "YES", "NO", or "MAYBE"
            knowledge: Knowledge text (optional, defaults to empty)
        """
        if annotation not in ["YES", "NO", "MAYBE"]:
            raise ValueError(f"Invalid annotation: {annotation}. Must be YES, NO, or MAYBE")
        
        df = self.get_annotator_sheet(annotator)
        
        # Check if meme_id already exists (handle NaN values)
        existing_idx = df[df['memeID'].astype(str) == str(meme_id)].index
        
        if len(existing_idx) > 0:
            # Update existing annotation
            idx = existing_idx[0]
            # Set values directly (dtype is already object from get_annotator_sheet)
            df.at[idx, 'annotation'] = str(annotation)
            df.at[idx, 'date'] = str(datetime.now().isoformat())
            df.at[idx, 'knowledge'] = str(knowledge) if knowledge else ''
        else:
            # Add new annotation
            new_row = pd.DataFrame({
                'memeID': [str(meme_id)],
                'annotation': [str(annotation)],
                'date': [str(datetime.now().isoformat())],
                'knowledge': [str(knowledge) if knowledge else '']
            })
            df = pd.concat([df, new_row], ignore_index=True)
        
        self.save_annotator_sheet(annotator, df)
        logger.info(f"Annotation saved: {annotator} - {meme_id} - {annotation}")
    
    def get_annotation(self, annotator: str, meme_id: str) -> Optional[Dict]:
        """
        Get annotation for a specific meme by an annotator.
        
        Args:
            annotator: Name of the annotator
            meme_id: ID of the meme
            
        Returns:
            Dictionary with annotation data or None if not found
        """
        df = self.get_annotator_sheet(annotator)
        row = df[df['memeID'].astype(str) == str(meme_id)]
        
        if len(row) == 0:
            return None
        
        result = row.iloc[0]
        return {
            'memeID': str(result['memeID']),
            'annotation': result['annotation'] if pd.notna(result['annotation']) else None,
            'date': result['date'] if pd.notna(result['date']) else None,
            'knowledge': result['knowledge'] if pd.notna(result['knowledge']) else None
        }
    
    def get_all_annotations_for_annotator(self, annotator: str) -> List[Dict]:
        """
        Get all annotations for a specific annotator.
        
        Args:
            annotator: Name of the annotator
            
        Returns:
            List of annotation dictionaries
        """
        df = self.get_annotator_sheet(annotator)
        return df.to_dict('records')
    
    def initialize_meme_ids_for_annotator(self, annotator: str, meme_ids: List[str]):
        """
        Initialize meme IDs for an annotator's sheet (add rows for memes that don't exist yet).
        
        Args:
            annotator: Name of the annotator
            meme_ids: List of meme IDs to add
        """
        df = self.get_annotator_sheet(annotator)
        existing_ids = set(df['memeID'].dropna().astype(str)) if len(df) > 0 else set()
        
        new_rows = []
        for meme_id in meme_ids:
            if str(meme_id) not in existing_ids:
                new_rows.append({
                    'memeID': meme_id,
                    'annotation': None,
                    'date': None,
                    'knowledge': None
                })
        
        if new_rows:
            new_df = pd.DataFrame(new_rows)
            df = pd.concat([df, new_df], ignore_index=True)
            self.save_annotator_sheet(annotator, df)
            logger.info(f"Initialized {len(new_rows)} new meme IDs for {annotator}")
