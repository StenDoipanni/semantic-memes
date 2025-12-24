"""
Data loader utility for loading meme images and extracted dimensions.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class DataLoader:
    """Loads meme images and extracted dimension data."""
    
    def __init__(self, 
                 img_dir: Optional[Path] = None,
                 output_dir: Optional[Path] = None):
        """
        Initialize the data loader.
        
        Args:
            img_dir: Directory containing meme images. Defaults to project img/ folder.
            output_dir: Directory containing extracted dimensions. Defaults to output_reversed/ folder.
        """
        # Get project root (parent of memes-annotation)
        project_root = Path(__file__).parent.parent.parent
        
        self.img_dir = img_dir or (project_root / "img" / "hateful-memes-img")
        self.output_dir = output_dir or (project_root / "output_reversed")
        
        # Cache for loaded data
        self._meme_cache: Dict[str, Dict[str, Any]] = {}
        self._dimension_cache: Dict[str, List[Dict[str, Any]]] = {}
    
    def get_available_memes(self) -> List[str]:
        """Get list of available meme filenames."""
        if not self.img_dir.exists():
            logger.warning(f"Image directory not found: {self.img_dir}")
            return []
        
        # Get all image files
        image_extensions = {'.png', '.jpg', '.jpeg', '.webp', '.gif'}
        meme_files = [
            f.name for f in self.img_dir.iterdir()
            if f.is_file() and f.suffix.lower() in image_extensions
        ]
        
        return sorted(meme_files)
    
    def get_meme_data(self, meme_name: str) -> Optional[Dict[str, Any]]:
        """
        Get all data for a specific meme.
        
        Args:
            meme_name: Name of the meme file (e.g., 'sea_monkeys.png')
            
        Returns:
            Dictionary containing image path, dimensions, and metadata
        """
        if meme_name in self._meme_cache:
            return self._meme_cache[meme_name]
        
        # Get image path
        image_path = self.img_dir / meme_name
        if not image_path.exists():
            logger.warning(f"Image not found: {image_path}")
            return None
        
        # Get base name without extension
        base_name = Path(meme_name).stem
        
        # Try to find main JSON-LD file (authoritative source)
        main_jsonld = self.output_dir / f"{base_name}_dimensions_reversed.jsonld"
        dimensions = []
        metadata = {}
        
        if main_jsonld.exists():
            try:
                with open(main_jsonld, 'r', encoding='utf-8') as f:
                    main_data = json.load(f)
                    metadata = main_data.get('metadata', {})
                    # Only use dimensions from main file (it's the authoritative source)
                    if 'dimensions' in main_data:
                        dimensions = main_data['dimensions']
                        # Deduplicate by @id to ensure no duplicates
                        seen_ids = set()
                        unique_dimensions = []
                        for dim in dimensions:
                            dim_id = dim.get('@id')
                            if dim_id and dim_id not in seen_ids:
                                seen_ids.add(dim_id)
                                unique_dimensions.append(dim)
                        dimensions = unique_dimensions
            except Exception as e:
                logger.error(f"Error loading main JSON-LD file: {e}")
        
        # If no dimensions from main file, try individual dimension files as fallback
        if not dimensions:
            dimensions = self._load_dimensions(base_name)
        
        # Build result
        result = {
            'image_path': str(image_path),
            'image_name': meme_name,
            'base_name': base_name,
            'dimensions': dimensions,
            'metadata': metadata
        }
        
        # Cache result
        self._meme_cache[meme_name] = result
        
        return result
    
    def _load_dimensions(self, base_name: str) -> List[Dict[str, Any]]:
        """Load all dimension files for a meme."""
        dimensions = []
        dimensions_dir = self.output_dir / "dimensions"
        
        if not dimensions_dir.exists():
            logger.warning(f"Dimensions directory not found: {dimensions_dir}")
            return dimensions
        
        # Iterate through dimension type directories
        for dim_type_dir in dimensions_dir.iterdir():
            if not dim_type_dir.is_dir():
                continue
            
            # Look for files matching the base name
            pattern = f"{base_name}_*.jsonld"
            for dim_file in dim_type_dir.glob(pattern):
                try:
                    with open(dim_file, 'r', encoding='utf-8') as f:
                        dim_data = json.load(f)
                        dimensions.append(dim_data)
                except Exception as e:
                    logger.error(f"Error loading dimension file {dim_file}: {e}")
        
        # Also check for files starting with base_name in the root dimensions folder
        for dim_file in dimensions_dir.rglob(f"{base_name}*.jsonld"):
            if dim_file.parent == dimensions_dir:
                continue  # Skip if already processed
            try:
                with open(dim_file, 'r', encoding='utf-8') as f:
                    dim_data = json.load(f)
                    if dim_data not in dimensions:  # Avoid duplicates
                        dimensions.append(dim_data)
            except Exception as e:
                logger.error(f"Error loading dimension file {dim_file}: {e}")
        
        return dimensions
    
    def get_dimension_types(self) -> List[str]:
        """Get list of all available dimension types."""
        dimensions_dir = self.output_dir / "dimensions"
        
        if not dimensions_dir.exists():
            return []
        
        # Get dimension types from directory names
        dim_types = [
            d.name for d in dimensions_dir.iterdir()
            if d.is_dir()
        ]
        
        # Also check for dimension types in loaded data
        for meme_data in self._meme_cache.values():
            for dim in meme_data.get('dimensions', []):
                dim_type = dim.get('@type')
                if dim_type and dim_type not in dim_types:
                    dim_types.append(dim_type)
        
        return sorted(set(dim_types))
    
    def clear_cache(self):
        """Clear the data cache."""
        self._meme_cache.clear()
        self._dimension_cache.clear()






