#!/usr/bin/env python3
"""
Test script for the Ollama Image Analyzer
Demonstrates different analysis prompts and usage patterns.
"""

from image_analyzer import OllamaImageAnalyzer
import sys

def test_different_prompts():
    """Test the analyzer with different prompts."""
    analyzer = OllamaImageAnalyzer()
    image_path = "batman-robin-global-warming.png"
    
    prompts = [
        "What is in this picture?",
        "Describe the characters and their actions in detail.",
        "What is the humor or joke in this image?",
        "What text or speech bubbles are visible?",
        "Is this a meme? If so, what makes it funny?"
    ]
    
    for i, prompt in enumerate(prompts, 1):
        print(f"\n{'='*80}")
        print(f"TEST {i}: {prompt}")
        print(f"{'='*80}")
        
        try:
            response = analyzer.analyze_image(image_path, prompt)
            analyzer.print_analysis(response)
        except Exception as e:
            print(f"Error in test {i}: {e}")

def test_custom_model():
    """Test with a different model if available."""
    print(f"\n{'='*80}")
    print("TESTING WITH DIFFERENT MODEL")
    print(f"{'='*80}")
    
    # You can change this to any other model you have
    custom_analyzer = OllamaImageAnalyzer(model_name="llama3.2:latest")
    
    try:
        response = custom_analyzer.analyze_image(
            "batman-robin-global-warming.png",
            "What do you see in this image?"
        )
        custom_analyzer.print_analysis(response)
    except Exception as e:
        print(f"Error with custom model: {e}")

if __name__ == "__main__":
    print("Ollama Image Analyzer - Test Suite")
    print("=" * 50)
    
    # Test with different prompts
    test_different_prompts()
    
    # Test with different model
    test_custom_model()
    
    print(f"\n{'='*80}")
    print("TESTING COMPLETE")
    print(f"{'='*80}") 