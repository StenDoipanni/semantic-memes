#!/usr/bin/env python3
"""
Image Analysis Script using Ollama with Gemma3:12b model
This script analyzes images by asking what's in the picture.
"""

import requests
import json
import sys
import os
from pathlib import Path
import base64

class OllamaImageAnalyzer:
    def __init__(self, model_name="gemma3:12b", ollama_url="http://localhost:11434"):
        """
        Initialize the Ollama image analyzer.
        
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
    
    def analyze_image(self, image_path, prompt="What is in this picture?"):
        """
        Analyze an image using Ollama with the specified model.
        
        Args:
            image_path (str): Path to the image file
            prompt (str): The question to ask about the image
            
        Returns:
            dict: Response from Ollama containing the analysis
        """
        # Check if image file exists
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")
        
        # Encode image to base64
        image_base64 = self.encode_image_to_base64(image_path)
        
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
                timeout=60
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
    
    def print_analysis(self, response):
        """
        Print the analysis results in a formatted way.
        
        Args:
            response (dict): The response from Ollama
        """
        print("=" * 60)
        print("IMAGE ANALYSIS RESULTS")
        print("=" * 60)
        print(f"Model: {self.model_name}")
        print(f"Response: {response.get('response', 'No response')}")
        print(f"Done: {response.get('done', False)}")
        if 'eval_count' in response:
            print(f"Evaluation count: {response['eval_count']}")
        if 'eval_duration' in response:
            print(f"Evaluation duration: {response['eval_duration']}ns")
        print("=" * 60)

def main():
    """Main function to run the image analysis."""
    # Default image path (the one in the workspace)
    default_image = "batman-robin-global-warming.png"
    
    # Get image path from command line argument or use default
    image_path = sys.argv[1] if len(sys.argv) > 1 else default_image

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
        analyzer = OllamaImageAnalyzer()
        
        print(f"Analyzing image: {image_path}")
        print("Using model: gemma3:12b")
        print("Question: What is in this picture?")
        print("-" * 60)
        
        # Analyze the image
        response = analyzer.analyze_image(image_path)
        
        # Print the results
        analyzer.print_analysis(response)
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 