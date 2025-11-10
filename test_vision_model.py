#!/usr/bin/env python3
"""
Simple test script for llama3.2-vision model
"""

import requests
import json
import time
from pathlib import Path
import base64

def test_vision_model():
    """Test the vision model with a simple image description task."""
    
    # Test image path
    image_path = Path("9_image_batch_2.png")
    if not image_path.exists():
        print(f"❌ Image not found: {image_path}")
        return False
    
    # Encode image to base64
    with open(image_path, "rb") as image_file:
        image_data = base64.b64encode(image_file.read()).decode('utf-8')
    
    # Prepare the request
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": "llama3.2-vision:11b",
        "prompt": "Describe what you see in this image in one sentence. Be specific about the text and visual elements.",
        "stream": False,
        "images": [image_data],
        "options": {
            "temperature": 0.1,
            "num_predict": 100
        }
    }
    
    print("🧪 Testing llama3.2-vision with image...")
    print("This may take a moment as the model loads...")
    
    try:
        response = requests.post(url, json=payload, timeout=300)  # 5 minute timeout
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Vision model response: {result.get('response', 'No response')}")
            return True
        else:
            print(f"❌ Vision model API error: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Vision model test failed: {e}")
        return False

if __name__ == "__main__":
    test_vision_model()
