# WP5-WP4 Bridge

This folder contains scripts to transform knowledge graph files from WP4 format to WP5 format.

## Overview

The script processes TTL (Turtle) knowledge graph files and:
1. Converts them to N-triples format
2. Transforms **only individual URIs** by adding an `image_id` prefix (`../[image_id]/`) to ensure no overlaps when graphs are merged
   - **Classes and properties are NOT transformed** - they remain as defined in the main ontology
   - Only individual instances (instances of classes) are transformed
3. Creates a `meme_object_[image_id]` individual of the `MemeObject` class (from main ontology)
4. Creates an `assertion_about_[image_id]` individual
5. Connects `meme_object_[image_id]` to `assertion_about_[image_id]` with the `hasAssertion` property (from main ontology)
6. Connects `assertion_about_[image_id]` to all individuals in the graph with the `relatedTo` property (from main ontology)

## Installation

Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Usage

```bash
python process_graphs.py <input_directory> [output_directory]
```

### Arguments

- `input_directory`: Directory containing TTL files (files matching pattern `*_refined_ontology.ttl`)
- `output_directory`: (Optional) Directory for output N-triples files. Defaults to `input_directory/transformed`

### Example

```bash
# Process files from output_reversed directory
python process_graphs.py ../output_reversed

# Specify custom output directory
python process_graphs.py ../output_reversed ./output
```

## Input File Format

The script expects TTL files with the naming pattern: `[image_id]_refined_ontology.ttl`

For example:
- `01235_refined_ontology.ttl` → image_id: `01235`
- `10865_refined_ontology.ttl` → image_id: `10865`

## Output Format

The script generates N-triples files with the naming pattern: `[image_id]_transformed.nt`

Each output file contains:
- All original triples with transformed URIs (adding `../[image_id]/` prefix)
- A `meme_object_[image_id]` individual of type `MemeObject`
- An `assertion_about_[image_id]` individual
- Triples connecting `meme_object_[image_id]` → `hasAssertion` → `assertion_about_[image_id]`
- Triples connecting `assertion_about_[image_id]` → `relatedTo` → [all individuals]

## URI Transformation

**Only individual URIs are transformed** - classes and properties remain unchanged (they come from the main ontology).

URIs of individuals are transformed by inserting `../[image_id]/` before the fragment or path component.

Examples:
- Individual (transformed): 
  - Original: `http://example.org/multimodal-taxonomy#man`
  - Transformed: `http://example.org/multimodal-taxonomy#../01235/man`
- Class (NOT transformed): 
  - `http://example.org/multimodal-taxonomy#VisualMaterial` (unchanged)
- Property (NOT transformed): 
  - `http://example.org/multimodal-taxonomy#relatedTo` (unchanged)
  - `http://example.org/multimodal-taxonomy#hasAssertion` (unchanged)

This ensures that when multiple graphs are merged:
- Individuals from different images don't overlap (they're namespaced by image_id)
- Classes and properties remain consistent across all graphs (from the main ontology)

