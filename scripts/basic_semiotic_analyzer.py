#!/usr/bin/env python3
"""
Entailment Trees Image Analysis Script
Implements the entailment trees approach for image analysis using Ollama with Gemma3:12b.
This script focuses on the first step: detailed image description using Greimas' plastic semiotics.
"""

import requests
import json
import sys
import os
import base64
from datetime import datetime
from pathlib import Path
import uuid

class EntailmentImageAnalyzer:
    def __init__(self, model_name="gemma3:12b", ollama_url="http://localhost:11434"):
        """
        Initialize the Entailment Image Analyzer.
        
        Args:
            model_name (str): The Ollama model to use (default: gemma3:12b)
            ollama_url (str): The Ollama server URL (default: localhost:11434)
        """
        self.model_name = model_name
        self.ollama_url = ollama_url
        self.api_endpoint = f"{ollama_url}/api/generate"
    
    def encode_image_to_base64(self, image_path):
        """
        Encode an image file to base64 string.
        
        Args:
            image_path (str): Path to the image file
            
        Returns:
            str: Base64 encoded image string
        """
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except FileNotFoundError:
            raise FileNotFoundError(f"Image file not found: {image_path}")
        except Exception as e:
            raise Exception(f"Error reading image file: {e}")
    
    def create_semiotic_prompt(self, image_path, fact_statement):
        """
        Create the first prompt focusing on Greimas' plastic semiotics.
        
        Args:
            image_path (str): Path to the image file
            fact_statement (str): The fact statement about the image
            
        Returns:
            str: Formatted prompt for the model
        """
        prompt = f"""Describe the given image. Carefully analyze the image content, paying close attention to Greimas "plastic semiotics", namely on:
- Topology: distribution of elements in space
- Eidetic: shapes, lines, borders and contours
- Cromatic: colors, saturation, values (amount of light)

In particular focus on the objects, actions, and attributes of each object to provide a detailed description. Additionally, a general statement related to the depicted situation is provided, which may offer cues about key objects or scenes to prioritize.

Note: Do not just follow the general statement, which is provided as a reference. You can only describe this image based on the image content and do not add any external knowledge to it.

Fact: {fact_statement}"""
        
        return prompt
    
    def analyze_image_semiotics(self, image_path, fact_statement):
        """
        Analyze an image using the semiotic prompt.
        
        Args:
            image_path (str): Path to the image file
            fact_statement (str): The fact statement about the image
            
        Returns:
            dict: Response from Ollama containing the analysis
        """
        # Check if image file exists
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")
        
        # Encode image to base64
        image_base64 = self.encode_image_to_base64(image_path)
        
        # Create the semiotic prompt
        prompt = self.create_semiotic_prompt(image_path, fact_statement)
        
        # Prepare the request payload
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "images": [image_base64],
            "stream": False
        }
        
        try:
            # Make the API request
            response = requests.post(
                self.api_endpoint,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=120  # Increased timeout for detailed analysis
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"Ollama API error: {response.status_code} - {response.text}")
                
        except requests.exceptions.ConnectionError:
            raise Exception("Could not connect to Ollama. Make sure Ollama is running on the specified URL.")
        except requests.exceptions.Timeout:
            raise Exception("Request timed out. The model might be taking too long to respond.")
        except Exception as e:
            raise Exception(f"Error making request to Ollama: {e}")
    
    def create_json_ld_structure(self, image_path, fact_statement, analysis_response):
        """
        Create a JSON-LD structure for the analysis results.
        
        Args:
            image_path (str): Path to the image file
            fact_statement (str): The fact statement about the image
            analysis_response (dict): The response from Ollama
            
        Returns:
            dict: JSON-LD structured data
        """
        # Generate unique identifiers
        analysis_id = str(uuid.uuid4())
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
                "greimas": "http://example.org/greimas/"
            },
            "@graph": [
                {
                    "@id": f"http://example.org/analysis/{analysis_id}",
                    "@type": "entailment:ImageAnalysis",
                    "name": f"Semiotic Analysis of {image_file.name}",
                    "description": "Detailed image analysis using Greimas' plastic semiotics",
                    "dateCreated": datetime.now().isoformat(),
                    "model": self.model_name,
                    "factStatement": fact_statement,
                    "imagePath": image_path,
                    "analysisStep": "semiotic_description",
                    "response": analysis_response.get('response', ''),
                    "evaluationCount": analysis_response.get('eval_count', 0),
                    "evaluationDuration": analysis_response.get('eval_duration', 0),
                    "done": analysis_response.get('done', False)
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
        
        return json_ld
    
    def save_json_ld(self, json_ld_data, output_path):
        """
        Save the JSON-LD data to a file.
        
        Args:
            json_ld_data (dict): The JSON-LD structured data
            output_path (str): Path where to save the JSON file
        """
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(json_ld_data, f, indent=2, ensure_ascii=False)
            print(f"JSON-LD data saved to: {output_path}")
        except Exception as e:
            raise Exception(f"Error saving JSON-LD file: {e}")
    
    def print_analysis_summary(self, json_ld_data):
        """
        Print a summary of the analysis results.
        
        Args:
            json_ld_data (dict): The JSON-LD structured data
        """
        analysis = json_ld_data["@graph"][0]
        
        print("=" * 80)
        print("ENTAILMENT TREES - SEMIOTIC ANALYSIS RESULTS")
        print("=" * 80)
        print(f"Analysis ID: {analysis['@id'].split('/')[-1]}")
        print(f"Image: {analysis['imagePath']}")
        print(f"Model: {analysis['model']}")
        print(f"Fact Statement: {analysis['factStatement']}")
        print(f"Date: {analysis['dateCreated']}")
        print(f"Evaluation Count: {analysis['evaluationCount']}")
        print(f"Evaluation Duration: {analysis['evaluationDuration']}ns")
        print("-" * 80)
        print("SEMIOTIC ANALYSIS:")
        print("-" * 80)
        print(analysis['response'])
        print("=" * 80)

def main():
    """Main function to run the entailment analysis."""
    # Default parameters
    default_image = "batman-robin-global-warming.png"
    default_fact = "Batman slapping Robin"
    
    # Get parameters from command line arguments or use defaults
    image_path = sys.argv[1] if len(sys.argv) > 1 else default_image
    fact_statement = sys.argv[2] if len(sys.argv) > 2 else default_fact

    # If image_path is just a filename, prepend img/ relative to project root
    if not os.path.isabs(image_path) and not os.path.dirname(image_path):
        # Get the project root directory (parent of scripts/)
        project_root = os.path.dirname(os.getcwd())
        image_path = os.path.join(project_root, "img", image_path)

    # Check if the image file exists
    if not os.path.exists(image_path):
        print(f"Error: Image file '{image_path}' not found.")
        print(f"Available files in img/:")
        project_root = os.path.dirname(os.getcwd())
        img_dir = os.path.join(project_root, "img")
        for file in os.listdir(img_dir):
            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                print(f"  - {file}")
        sys.exit(1)
    
    try:
        # Initialize the analyzer
        analyzer = EntailmentImageAnalyzer()
        
        print(f"Starting Entailment Trees Analysis")
        print(f"Image: {image_path}")
        print(f"Fact Statement: {fact_statement}")
        print(f"Model: gemma3:12b")
        print(f"Step: Semiotic Description (Greimas' Plastic Semiotics)")
        print("-" * 80)
        
        # Analyze the image
        response = analyzer.analyze_image_semiotics(image_path, fact_statement)
        
        # Create JSON-LD structure
        json_ld_data = analyzer.create_json_ld_structure(image_path, fact_statement, response)
        
        # Generate output filename
        image_name = Path(image_path).stem
        output_filename = os.path.join("outputs", f"entailment_analysis_{image_name}_step1_semiotics.json")
        
        # Save to JSON-LD file
        analyzer.save_json_ld(json_ld_data, output_filename)
        
        # Print summary
        analyzer.print_analysis_summary(json_ld_data)
        
        print(f"\n✅ Analysis completed successfully!")
        print(f"📁 Results saved to: {output_filename}")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 