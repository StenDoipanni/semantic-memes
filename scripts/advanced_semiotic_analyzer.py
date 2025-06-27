#!/usr/bin/env python3
"""
Structured Semiotic Analysis using Greimas' Plastic Semiotics with PropBank Roles
Analyzes images using topology, eidetic, and chromatic levels with formal semantic role labeling.
Creates organized output folders for each image analysis.
"""

import json
import base64
import requests
import uuid
from datetime import datetime
from pathlib import Path
import jsonschema
from jsonschema import validate
import sys
import os
import time

def encode_image_to_base64(image_path):
    """Encode image to base64 string."""
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except FileNotFoundError:
        print(f"Error: Image file '{image_path}' not found.")
        return None
    except Exception as e:
        print(f"Error encoding image: {e}")
        return None

def load_json_schema(schema_path):
    """Load and validate JSON schema."""
    try:
        with open(schema_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Schema file '{schema_path}' not found.")
        return None
    except json.JSONDecodeError as e:
        print(f"Error parsing schema file: {e}")
        return None

def load_prompt_template(prompt_path):
    """Load prompt template."""
    try:
        with open(prompt_path, 'r') as f:
            return f.read()
    except FileNotFoundError:
        print(f"Error: Prompt file '{prompt_path}' not found.")
        return None

def call_ollama_api(image_base64, prompt):
    """Call Ollama API with image and prompt."""
    url = "http://localhost:11434/api/generate"
    
    payload = {
        "model": "gemma3:12b",
        "prompt": prompt,
        "images": [image_base64],
        "stream": False,
        "options": {
            "temperature": 0.1,
            "top_p": 0.9,
            "num_predict": 4000
        }
    }
    
    try:
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error calling Ollama API: {e}")
        return None

def extract_json_from_response(response_text):
    """Extract JSON from response text, handling common formatting issues."""
    # Remove any text before the first {
    start_idx = response_text.find('{')
    if start_idx == -1:
        return None
    
    # Remove any text after the last }
    end_idx = response_text.rfind('}')
    if end_idx == -1:
        return None
    
    json_str = response_text[start_idx:end_idx + 1]
    
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        print(f"JSON string: {json_str[:200]}...")
        return None

def fix_relation_types(result):
    """Fix common relation type errors by mapping invalid types to valid ones."""
    if not result or 'semanticRelations' not in result:
        return result
    
    # Common mappings from invalid to valid relation types
    relation_mappings = {
        'observation_of': 'interaction',
        'looking_at': 'interaction', 
        'staring_at': 'interaction',
        'watching': 'interaction',
        'viewing': 'interaction',
        'seeing': 'interaction',
        'gazing_at': 'interaction',
        'facing': 'spatial_relation',
        'near': 'proximity',
        'close_to': 'proximity',
        'next_to': 'proximity',
        'beside': 'proximity',
        'behind': 'spatial_relation',
        'in_front_of': 'spatial_relation',
        'above': 'spatial_relation',
        'below': 'spatial_relation',
        'on_top_of': 'spatial_relation',
        'under': 'spatial_relation',
        'inside': 'spatial_relation',
        'outside': 'spatial_relation',
        'talking_to': 'interaction',
        'speaking_to': 'interaction',
        'conversing_with': 'interaction',
        'discussing_with': 'interaction',
        'arguing_with': 'opposition',
        'fighting_with': 'opposition',
        'helping': 'support',
        'assisting': 'support',
        'teaching': 'mentorship',
        'learning_from': 'mentorship',
        'protecting': 'protection',
        'guarding': 'protection',
        'leading': 'guidance',
        'following': 'guidance',
        'working_with': 'collaboration',
        'teaming_with': 'collaboration',
        'partnering_with': 'partnership',
        'allied_with': 'alliance',
        'friends_with': 'friendship',
        'accompanying': 'companionship',
        'similar_to': 'similar_to',
        'different_from': 'contrasts_with',
        'opposed_to': 'opposition',
        'against': 'opposition',
        'causing': 'causal_relation',
        'resulting_in': 'causal_relation',
        'part_of': 'part_of',
        'belongs_to': 'part_of',
        'acting_on': 'action_on',
        'affecting': 'action_on'
    }
    
    # Fix relationships
    if 'relationships' in result['semanticRelations']:
        for relation in result['semanticRelations']['relationships']:
            if 'relationType' in relation:
                invalid_type = relation['relationType']
                if invalid_type in relation_mappings:
                    valid_type = relation_mappings[invalid_type]
                    print(f"Fixed relation type: '{invalid_type}' -> '{valid_type}'")
                    relation['relationType'] = valid_type
    
    return result

def validate_analysis_result(result, schema):
    """Validate analysis result against schema."""
    try:
        validate(instance=result, schema=schema)
        return True
    except jsonschema.exceptions.ValidationError as e:
        print(f"Schema validation error: {e}")
        
        # Try to fix common relation type errors
        if "relationType" in str(e):
            print("Attempting to fix relation type errors...")
            fixed_result = fix_relation_types(result)
            try:
                validate(instance=fixed_result, schema=schema)
                print("Successfully fixed relation type errors!")
                return True
            except jsonschema.exceptions.ValidationError as e2:
                print(f"Still has validation errors after fixing: {e2}")
                
                # If still failing, try to move invalid relations to extraSchemaRelations
                print("Moving invalid relations to extraSchemaRelations...")
                result_with_extra = move_invalid_relations_to_extra(result)
                try:
                    validate(instance=result_with_extra, schema=schema)
                    print("Successfully moved invalid relations to extraSchemaRelations!")
                    # Update the result to use the fixed version
                    result.clear()
                    result.update(result_with_extra)
                    return True
                except jsonschema.exceptions.ValidationError as e3:
                    print(f"Still has validation errors after moving to extra: {e3}")
                    return False
        
        return False
    except Exception as e:
        print(f"Validation error: {e}")
        return False

def move_invalid_relations_to_extra(result):
    """Move relations with invalid relationType to extraSchemaRelations."""
    if not result or 'semanticRelations' not in result:
        return result
    
    # Initialize extraSchemaRelations if it doesn't exist
    if 'extraSchemaRelations' not in result['semanticRelations']:
        result['semanticRelations']['extraSchemaRelations'] = []
    
    # Valid relation types from schema
    valid_relation_types = [
        "action_on", "spatial_relation", "temporal_relation", "causal_relation", 
        "part_of", "similar_to", "contrasts_with", "partnership", "companionship", 
        "interaction", "proximity", "hierarchy", "support", "opposition", 
        "collaboration", "guidance", "protection", "mentorship", "friendship", "alliance"
    ]
    
    # Move invalid relations to extraSchemaRelations
    valid_relations = []
    moved_relations = []
    for relation in result['semanticRelations']['relationships']:
        if 'relationType' in relation:
            if relation['relationType'] in valid_relation_types:
                valid_relations.append(relation)
            else:
                # Move to extraSchemaRelations
                extra_relation = relation.copy()
                extra_relation['originalRelationType'] = relation['relationType']
                extra_relation['relationType'] = relation['relationType']  # Keep original as relationType
                result['semanticRelations']['extraSchemaRelations'].append(extra_relation)
                moved_relations.append(relation['relationType'])
                print(f"Moved relation '{relation['relationType']}' to extraSchemaRelations")
    
    # Update the relationships array with only valid relations
    result['semanticRelations']['relationships'] = valid_relations
    
    # Print summary of moved relations
    if moved_relations:
        print(f"📋 Moved {len(moved_relations)} relation(s) to extraSchemaRelations: {', '.join(moved_relations)}")
    
    return result

def create_analysis_folder(image_path):
    """Create folder for analysis output based on image name, inside outputs/."""
    image_name = Path(image_path).stem
    folder_name = os.path.join("outputs", f"analysis_{image_name}")
    os.makedirs(folder_name, exist_ok=True)
    print(f"Created analysis folder: {folder_name}")
    return folder_name

def save_analysis_files(result, raw_response, prompt, fact_statement, image_path, output_folder):
    """Save all analysis files to the output folder."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save structured JSON result
    json_path = os.path.join(output_folder, f"structured_analysis_{timestamp}.json")
    try:
        with open(json_path, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"Structured analysis saved to: {json_path}")
    except Exception as e:
        print(f"Error saving structured analysis: {e}")
    
    # Save raw LLM response
    raw_response_path = os.path.join(output_folder, f"raw_response_{timestamp}.txt")
    try:
        with open(raw_response_path, 'w') as f:
            f.write(raw_response)
        print(f"Raw response saved to: {raw_response_path}")
    except Exception as e:
        print(f"Error saving raw response: {e}")
    
    # Save prompt used
    prompt_path = os.path.join(output_folder, f"prompt_{timestamp}.txt")
    try:
        with open(prompt_path, 'w') as f:
            f.write(prompt)
        print(f"Prompt saved to: {prompt_path}")
    except Exception as e:
        print(f"Error saving prompt: {e}")
    
    # Save analysis summary
    summary_path = os.path.join(output_folder, f"summary_{timestamp}.txt")
    try:
        with open(summary_path, 'w') as f:
            f.write("SEMIOTIC ANALYSIS SUMMARY\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Image: {image_path}\n")
            f.write(f"Fact Statement: {fact_statement}\n")
            f.write(f"Analysis ID: {result['metadata']['analysisId']}\n")
            f.write(f"Model: {result['metadata']['model']}\n")
            # Handle both possible timestamp field names
            if 'timestamp' in result['metadata']:
                f.write(f"Timestamp: {result['metadata']['timestamp']}\n")
            elif 'dateCreated' in result['metadata']:
                f.write(f"Date Created: {result['metadata']['dateCreated']}\n")
            f.write("\n")
            
            f.write("ANALYSIS OVERVIEW\n")
            f.write("-" * 20 + "\n")
            f.write(f"Participants: {len(result['semanticRelations']['participants'])}\n")
            f.write(f"Objects: {len(result['objects'])}\n")
            f.write(f"Overall Mood: {result['overallImpression']['mood']}\n")
            f.write(f"Tension Level: {result['overallImpression']['tension']}\n\n")
            
            f.write("PARTICIPANTS\n")
            f.write("-" * 15 + "\n")
            for participant in result['semanticRelations']['participants']:
                f.write(f"- {participant['element']}\n")
                if 'propbankRoles' in participant:
                    f.write(f"  PropBank Roles: {', '.join(participant['propbankRoles'])}\n")
                if 'attributes' in participant:
                    for attr in participant['attributes']:
                        f.write(f"  {attr['attribute']}: {attr['value']} ({attr['category']})\n")
                f.write("\n")
            
            f.write("OBJECTS\n")
            f.write("-" * 8 + "\n")
            for obj in result['objects']:
                f.write(f"- {obj['name']} ({obj['category']})\n")
                f.write(f"  PropBank Role: {obj['propbankRole']}\n")
                if 'attributes' in obj:
                    for attr in obj['attributes']:
                        f.write(f"  {attr['attribute']}: {attr['value']} ({attr['semioticLevel']})\n")
                f.write("\n")
            
            f.write("RELATIONS\n")
            f.write("-" * 11 + "\n")
            for relation in result['semanticRelations']['relationships']:
                f.write(f"- {relation['participant1']} {relation['relationType']} {relation['participant2']}\n")
                f.write(f"  PropBank Role: {relation['propbankRole']}\n")
                f.write(f"  Description: {relation['description']}\n\n")
        
        print(f"Analysis summary saved to: {summary_path}")
    except Exception as e:
        print(f"Error saving summary: {e}")
    
    return json_path

def analyze_image(image_path, fact_statement, schema_path="schemas/semiotic_schema.json", prompt_path="prompts/structured_semiotic_prompt.txt"):
    """Main function to analyze image using structured semiotic approach."""
    
    start_time = time.time()
    
    # Load schema and prompt
    schema = load_json_schema(schema_path)
    if not schema:
        return None, None, None
    
    prompt_template = load_prompt_template(prompt_path)
    if not prompt_template:
        return None, None, None
    
    # Encode image
    image_base64 = encode_image_to_base64(image_path)
    if not image_base64:
        return None, None, None
    
    # Prepare prompt
    prompt = prompt_template.format(
        image_path=image_path,
        fact_statement=fact_statement
    )
    
    print("Calling Ollama API...")
    response = call_ollama_api(image_base64, prompt)
    if not response:
        return None, None, None
    
    raw_response = response.get('response', '')
    
    # Extract JSON from response
    result = extract_json_from_response(raw_response)
    if not result:
        print("Failed to extract JSON from response")
        return None, None, None
    
    # Validate result
    if not validate_analysis_result(result, schema):
        print("Analysis result failed schema validation")
        return None, None, None
    
    end_time = time.time()
    analysis_time = end_time - start_time
    print(f"⏱️  Analysis completed in {analysis_time:.2f} seconds")
    
    return result, raw_response, prompt

def convert_to_json_ld(result, image_path, fact_statement, raw_response):
    """Convert structured analysis result to JSON-LD format."""
    analysis_id = result['metadata']['analysisId']
    image_id = str(uuid.uuid4())
    
    # Get file information
    image_file = Path(image_path)
    file_size = image_file.stat().st_size if image_file.exists() else 0
    
    # Create JSON-LD structure
    json_ld = {
        "@context": {
            "@vocab": "http://schema.org/",
            "entailment": "http://example.org/entailment/",
            "semiotics": "http://example.org/semiotics/",
            "greimas": "http://example.org/greimas/",
            "propbank": "http://example.org/propbank/"
        },
        "@graph": [
            {
                "@id": f"http://example.org/analysis/{analysis_id}",
                "@type": "entailment:StructuredImageAnalysis",
                "name": f"Structured Semiotic Analysis of {image_file.name}",
                "description": "Comprehensive image analysis using Greimas' plastic semiotics with PropBank roles",
                "dateCreated": result['metadata'].get('dateCreated', datetime.now().isoformat()),
                "model": result['metadata']['model'],
                "factStatement": fact_statement,
                "imagePath": image_path,
                "analysisStep": "structured_semiotic_description",
                "rawResponse": raw_response,
                "evaluationCount": result['metadata'].get('evaluationCount', 0),
                "evaluationDuration": result['metadata'].get('evaluationDuration', 0),
                "done": result['metadata'].get('done', True)
            },
            {
                "@id": f"http://example.org/image/{image_id}",
                "@type": "ImageObject",
                "name": image_file.name,
                "contentUrl": f"file://{os.path.abspath(image_path)}",
                "fileSize": file_size,
                "encodingFormat": image_file.suffix.lower().replace('.', ''),
                "isPartOf": f"http://example.org/analysis/{analysis_id}"
            },
            {
                "@id": f"http://example.org/semiotics/{analysis_id}",
                "@type": "semiotics:PlasticSemiotics",
                "topology": "Distribution of elements in space analysis",
                "eidetic": "Shapes, lines, borders and contours analysis", 
                "chromatic": "Colors, saturation, values analysis",
                "isPartOf": f"http://example.org/analysis/{analysis_id}"
            }
        ]
    }
    
    # Add participants as separate nodes
    for i, participant in enumerate(result['semanticRelations']['participants']):
        participant_id = f"http://example.org/participant/{analysis_id}_{i}"
        json_ld["@graph"].append({
            "@id": participant_id,
            "@type": "entailment:Participant",
            "element": participant['element'],
            "propbankRoles": participant.get('propbankRoles', []),
            "attributes": participant.get('attributes', []),
            "isPartOf": f"http://example.org/analysis/{analysis_id}"
        })
    
    # Add objects as separate nodes
    for i, obj in enumerate(result['objects']):
        object_id = f"http://example.org/object/{analysis_id}_{i}"
        json_ld["@graph"].append({
            "@id": object_id,
            "@type": "entailment:Object",
            "name": obj['name'],
            "category": obj['category'],
            "propbankRole": obj['propbankRole'],
            "attributes": obj.get('attributes', []),
            "isPartOf": f"http://example.org/analysis/{analysis_id}"
        })
    
    # Add relationships as separate nodes
    for i, relation in enumerate(result['semanticRelations']['relationships']):
        relation_id = f"http://example.org/relation/{analysis_id}_{i}"
        json_ld["@graph"].append({
            "@id": relation_id,
            "@type": "entailment:Relationship",
            "participant1": relation['participant1'],
            "participant2": relation['participant2'],
            "relationType": relation['relationType'],
            "propbankRole": relation['propbankRole'],
            "description": relation['description'],
            "isPartOf": f"http://example.org/analysis/{analysis_id}"
        })
    
    # Add overall impression
    json_ld["@graph"].append({
        "@id": f"http://example.org/impression/{analysis_id}",
        "@type": "entailment:OverallImpression",
        "mood": result['overallImpression']['mood'],
        "tension": result['overallImpression']['tension'],
        "isPartOf": f"http://example.org/analysis/{analysis_id}"
    })
    
    return json_ld

def save_json_ld_output(json_ld_data, image_path):
    """Save JSON-LD output to outputs folder."""
    image_name = Path(image_path).stem
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = os.path.join("outputs", f"structured_entailment_analysis_{image_name}_step1_semiotics_{timestamp}.json")
    
    try:
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(json_ld_data, f, indent=2, ensure_ascii=False)
        print(f"JSON-LD analysis saved to: {output_filename}")
        return output_filename
    except Exception as e:
        print(f"Error saving JSON-LD file: {e}")
        return None

def main():
    if len(sys.argv) < 3:
        print("Usage: python advanced_semiotic_analyzer.py <image_path> <fact_statement> [--json-ld]")
        print("Example: python advanced_semiotic_analyzer.py batman-robin-global-warming.png 'Batman and Robin are discussing global warming'")
        print("Example: python advanced_semiotic_analyzer.py batman-robin-global-warming.png 'Batman and Robin are discussing global warming' --json-ld")
        sys.exit(1)
    
    image_path = sys.argv[1]
    fact_statement = sys.argv[2]
    output_json_ld = "--json-ld" in sys.argv

    # If image_path is just a filename, prepend img/ relative to project root
    if not os.path.isabs(image_path) and not os.path.dirname(image_path):
        # Get the project root directory (parent of scripts/)
        project_root = os.path.dirname(os.getcwd())
        image_path = os.path.join(project_root, "img", image_path)

    print(f"Analyzing image: {image_path}")
    print(f"Fact statement: {fact_statement}")
    print(f"Output format: {'JSON-LD' if output_json_ld else 'Structured JSON'}")
    print("-" * 50)
    
    # Perform analysis
    result, raw_response, prompt = analyze_image(image_path, fact_statement)
    
    if result:
        if output_json_ld:
            # Convert to JSON-LD and save
            json_ld_data = convert_to_json_ld(result, image_path, fact_statement, raw_response)
            json_path = save_json_ld_output(json_ld_data, image_path)
            
            if json_path:
                print("\nJSON-LD Analysis Summary:")
                print(f"- Analysis ID: {result['metadata']['analysisId']}")
                print(f"- Model: {result['metadata']['model']}")
                print(f"- Participants: {len(result['semanticRelations']['participants'])}")
                print(f"- Objects: {len(result['objects'])}")
                print(f"- Mood: {result['overallImpression']['mood']}")
                print(f"- Tension: {result['overallImpression']['tension']}")
                print(f"- JSON-LD saved to: {json_path}")
            else:
                print("Failed to save JSON-LD output")
                sys.exit(1)
        else:
            # Create output folder and save structured files
            output_folder = create_analysis_folder(image_path)
            json_path = save_analysis_files(result, raw_response, prompt, fact_statement, image_path, output_folder)
            
            # Print summary
            print("\nAnalysis Summary:")
            print(f"- Analysis ID: {result['metadata']['analysisId']}")
            print(f"- Model: {result['metadata']['model']}")
            print(f"- Participants: {len(result['semanticRelations']['participants'])}")
            print(f"- Objects: {len(result['objects'])}")
            print(f"- Mood: {result['overallImpression']['mood']}")
            print(f"- Tension: {result['overallImpression']['tension']}")
            print(f"- All files saved in folder: {output_folder}")
        
    else:
        print("Analysis failed")
        sys.exit(1)

if __name__ == "__main__":
    main() 