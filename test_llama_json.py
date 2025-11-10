#!/usr/bin/env python3
"""
Test script to see what llama3.2-vision returns for JSON prompts
"""

import requests
import json
import base64
from pathlib import Path

def test_llama_json_response():
    """Test what llama3.2-vision returns for a JSON prompt."""
    
    # Test image path
    image_path = Path("9_image_batch_2.png")
    if not image_path.exists():
        print(f"❌ Image not found: {image_path}")
        return False
    
    # Encode image to base64
    with open(image_path, "rb") as image_file:
        image_data = base64.b64encode(image_file.read()).decode('utf-8')
    
    # Simple JSON prompt
    prompt = """Please analyze this image and return a JSON response with the following structure:
{
    "instance_name": "example_name",
    "label": "example_label", 
    "description": "example_description"
}

Please respond with ONLY the JSON, no other text."""
    
    # Prepare the request
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": "llama3.2-vision:11b",
        "prompt": prompt,
        "stream": False,
        "images": [image_data],
        "options": {
            "temperature": 0.1,
            "num_predict": 200
        }
    }
    
    print("🧪 Testing llama3.2-vision JSON response...")
    print("This may take a moment...")
    
    try:
        response = requests.post(url, json=payload, timeout=300)
        if response.status_code == 200:
            result = response.json()
            raw_response = result.get('response', 'No response')
            print(f"✅ Raw response: {raw_response}")
            
            # Try to parse as JSON
            try:
                json_data = json.loads(raw_response)
                print(f"✅ Valid JSON: {json_data}")
                return True
            except json.JSONDecodeError as e:
                print(f"❌ JSON parsing failed: {e}")
                print("Raw response was not valid JSON")
                return False
        else:
            print(f"❌ API error: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    test_llama_json_response()
