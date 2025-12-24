"""
Streamlit Meme Annotation Service

A web-based service for viewing and annotating meme analysis results.
"""

import streamlit as st
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
import sys
from datetime import datetime

# Add parent directory to path to import project modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.data_loader import DataLoader
from utils.annotation_manager import AnnotationManager

# Page configuration
st.set_page_config(
    page_title="Meme Annotation Service",
    page_icon="🖼️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'data_loader' not in st.session_state:
    st.session_state.data_loader = DataLoader()
if 'annotation_manager' not in st.session_state:
    st.session_state.annotation_manager = AnnotationManager()
if 'selected_meme' not in st.session_state:
    st.session_state.selected_meme = None
if 'current_annotator' not in st.session_state:
    st.session_state.current_annotator = None
if 'meme_ids_initialized' not in st.session_state:
    st.session_state.meme_ids_initialized = False
if 'pending_annotation' not in st.session_state:
    st.session_state.pending_annotation = {}  # {meme_name: annotation_value}

def show_user_selection():
    """Display user selection page."""
    st.title("🖼️ Meme Annotation Service")
    st.markdown("---")
    st.markdown("### Select Annotator")
    
    annotators = AnnotationManager.ANNOTATORS
    
    selected_annotator = st.selectbox(
        "Choose your name:",
        options=annotators,
        index=0
    )
    
    if st.button("Start Annotating", type="primary", use_container_width=True):
        st.session_state.current_annotator = selected_annotator
        # Initialize meme IDs for this annotator
        available_memes = st.session_state.data_loader.get_available_memes()
        if available_memes:
            # Get first 100 memes (or all if less than 100)
            meme_ids_to_init = available_memes[:100]
            st.session_state.annotation_manager.initialize_meme_ids_for_annotator(
                selected_annotator,
                meme_ids_to_init
            )
            st.session_state.meme_ids_initialized = True
        st.rerun()

def main():
    """Main application entry point."""
    
    # Check if user is selected
    if st.session_state.current_annotator is None:
        show_user_selection()
        return
    
    # Sidebar
    with st.sidebar:
        st.title("🖼️ Meme Annotation")
        st.markdown("---")
        
        # Show current annotator
        st.info(f"**Annotator:** {st.session_state.current_annotator}")
        if st.button("Change Annotator"):
            st.session_state.current_annotator = None
            st.session_state.meme_ids_initialized = False
            st.rerun()
        
        st.markdown("---")
        
        # Meme selection
        st.subheader("Select Meme")
        available_memes = st.session_state.data_loader.get_available_memes()
        
        if not available_memes:
            st.error("No memes found in the hateful-memes-img folder.")
            return
        
        # Store previous meme before selectbox changes it
        previous_meme = st.session_state.selected_meme
        
        selected_meme_name = st.selectbox(
            "Choose a meme:",
            options=available_memes,
            index=0 if st.session_state.selected_meme is None else 
                  available_memes.index(st.session_state.selected_meme) if st.session_state.selected_meme in available_memes else 0
        )
        
        # If meme changed via selectbox, save any pending annotation for previous meme
        if (previous_meme and 
            previous_meme != selected_meme_name and
            previous_meme in st.session_state.pending_annotation):
            annotation_value = st.session_state.pending_annotation[previous_meme]
            knowledge_text = ""
            st.session_state.annotation_manager.save_annotation(
                st.session_state.current_annotator,
                previous_meme,
                annotation_value,
                knowledge_text
            )
            del st.session_state.pending_annotation[previous_meme]
            st.success(f"Annotation saved for {previous_meme}: {annotation_value}")
        
        st.session_state.selected_meme = selected_meme_name
        
        st.markdown("---")
        
        # Show current annotation status
        existing_annotation = st.session_state.annotation_manager.get_annotation(
            st.session_state.current_annotator,
            selected_meme_name
        )
        if existing_annotation and existing_annotation.get('annotation'):
            st.subheader("Current Annotation")
            st.success(f"**{existing_annotation['annotation']}**")
            if existing_annotation.get('date'):
                st.caption(f"Annotated on: {existing_annotation['date']}")
    
    # Main content area
    if st.session_state.selected_meme:
        display_meme_analysis(st.session_state.selected_meme)
    else:
        st.info("Please select a meme from the sidebar to begin.")

def display_meme_analysis(meme_name: str):
    """Display the meme and its analysis."""
    
    meme_data = st.session_state.data_loader.get_meme_data(meme_name)
    
    if not meme_data:
        st.error(f"No data found for meme: {meme_name}")
        return
    
    # Image display
    image_path = meme_data.get('image_path')
    if image_path and Path(image_path).exists():
        col1, col2, col3 = st.columns([1, 3, 1])
        with col2:
            st.image(image_path, caption=meme_name)
    else:
        st.warning(f"Image not found: {image_path}")
    
    st.markdown("---")
    
    dimensions = meme_data.get('dimensions', [])
    if not dimensions:
        st.info("No dimensions found for this meme.")
        # Still allow annotation even if no dimensions
        knowledge_text = ""
        display_annotation_buttons(meme_name, knowledge_text)
        # Show Next button even when no dimensions
        st.markdown("---")
        available_memes = st.session_state.data_loader.get_available_memes()
        if meme_name in available_memes:
            current_index = available_memes.index(meme_name)
            if current_index < len(available_memes) - 1:
                next_meme = available_memes[current_index + 1]
                if st.button("➡️ Next Meme", key="next_meme_button_no_dims", type="primary", use_container_width=True):
                    # Save any pending annotation for current meme before moving to next
                    if meme_name in st.session_state.pending_annotation:
                        annotation_value = st.session_state.pending_annotation[meme_name]
                        st.session_state.annotation_manager.save_annotation(
                            st.session_state.current_annotator,
                            meme_name,
                            annotation_value,
                            knowledge_text
                        )
                        del st.session_state.pending_annotation[meme_name]
                        st.success(f"Annotation saved: {annotation_value}")
                    st.session_state.selected_meme = next_meme
                    st.rerun()
            else:
                st.info("This is the last meme in the list.")
        return
    
    # Extract focus dimensions and deduplicate by @id
    seen_ids = set()
    toxicity_dims = []
    analogical_dims = []
    
    for d in dimensions:
        dim_id = d.get('@id')
        dim_type = d.get('@type')
        
        # Skip if we've already seen this dimension
        if dim_id and dim_id in seen_ids:
            continue
        
        seen_ids.add(dim_id)
        
        if dim_type == 'ToxicityAssessment':
            toxicity_dims.append(d)
        elif dim_type == 'AnalogicalMapping':
            analogical_dims.append(d)
    
    # Display ToxicityAssessment
    if toxicity_dims:
        st.markdown("### ToxicityAssessment")
        for idx, dim in enumerate(toxicity_dims):
            description = dim.get('description', '')
            if description and description.strip():
                st.markdown(description)
            if idx < len(toxicity_dims) - 1:
                st.markdown("---")
    
    # Display AnalogicalMapping
    if analogical_dims:
        if toxicity_dims:
            st.markdown("---")
        st.markdown("### AnalogicalMapping")
        for idx, dim in enumerate(analogical_dims):
            description = dim.get('description', '')
            if description and description.strip():
                st.markdown(description)
            if idx < len(analogical_dims) - 1:
                st.markdown("---")
    
    # Show message if no focus dimensions found
    if not toxicity_dims and not analogical_dims:
        st.info("No ToxicityAssessment or AnalogicalMapping dimensions found for this meme.")
    
    # Combine all descriptions for knowledge field (for now, empty as per user request)
    knowledge_text = ""
    
    # Display annotation buttons
    st.markdown("---")
    display_annotation_buttons(meme_name, knowledge_text)
    
    # Next button at the bottom
    st.markdown("---")
    available_memes = st.session_state.data_loader.get_available_memes()
    if meme_name in available_memes:
        current_index = available_memes.index(meme_name)
        if current_index < len(available_memes) - 1:
            next_meme = available_memes[current_index + 1]
            if st.button("➡️ Next Meme", key="next_meme_button", type="primary", use_container_width=True):
                # Save any pending annotation for current meme before moving to next
                if meme_name in st.session_state.pending_annotation:
                    annotation_value = st.session_state.pending_annotation[meme_name]
                    knowledge_text = ""  # Can be enhanced later
                    st.session_state.annotation_manager.save_annotation(
                        st.session_state.current_annotator,
                        meme_name,
                        annotation_value,
                        knowledge_text
                    )
                    # Remove from pending after saving
                    del st.session_state.pending_annotation[meme_name]
                    st.success(f"Annotation saved: {annotation_value}")
                
                st.session_state.selected_meme = next_meme
                st.rerun()
        else:
            st.info("This is the last meme in the list.")

def display_annotation_buttons(meme_name: str, knowledge_text: str):
    """Display annotation buttons for the meme."""
    
    st.markdown("### Annotation")
    st.markdown("**Do you agree with the assertions above?**")
    
    # Get existing annotation
    existing_annotation = st.session_state.annotation_manager.get_annotation(
        st.session_state.current_annotator,
        meme_name
    )
    
    existing_value = None
    if existing_annotation and existing_annotation.get('annotation'):
        existing_value = existing_annotation['annotation']
    
    # Check if there's a pending annotation (not yet saved)
    pending_value = st.session_state.pending_annotation.get(meme_name)
    display_value = pending_value if pending_value else existing_value
    
    # Use radio buttons for better state management
    annotation_options = ["✅ YES", "❌ NO", "❓ MAYBE"]
    annotation_values = ["YES", "NO", "MAYBE"]
    
    # Find current selection index
    current_index = 0
    if display_value:
        try:
            current_index = annotation_values.index(display_value)
        except ValueError:
            current_index = 0
    
    selected_option = st.radio(
        "**Do you agree with the assertions above?**",
        options=annotation_options,
        index=current_index,
        key=f"annotation_radio_{meme_name}",
        horizontal=True
    )
    
    # Update pending annotation when selection changes
    selected_value = annotation_values[annotation_options.index(selected_option)]
    if selected_value != display_value:
        st.session_state.pending_annotation[meme_name] = selected_value
    
    # Show current annotation status
    if display_value:
        if pending_value and pending_value != existing_value:
            st.info(f"Selected annotation: **{display_value}** (not yet saved - click Next to save)")
        else:
            st.info(f"Current annotation: **{display_value}**")


if __name__ == "__main__":
    main()
