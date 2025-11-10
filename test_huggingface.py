#!/usr/bin/env python3
"""
Simple test script to verify HuggingFace/Qwen2-VL works correctly.
"""

import sys
from pathlib import Path

# Add repo root to path
REPO_ROOT = Path(__file__).parent
sys.path.insert(0, str(REPO_ROOT))

import torch
from PIL import Image
from transformers import AutoProcessor, AutoModelForVision2Seq
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_gpu():
    """Test GPU availability."""
    print("=" * 70)
    print("GPU TEST")
    print("=" * 70)
    print(f"CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"GPU Device: {torch.cuda.get_device_name(0)}")
        print(f"GPU Count: {torch.cuda.device_count()}")
        print(f"Current GPU: {torch.cuda.current_device()}")
        print(f"CUDA Version: {torch.version.cuda}")
    else:
        print("❌ CUDA not available!")
    print()

def test_model_loading():
    """Test loading Qwen2-VL model."""
    print("=" * 70)
    print("MODEL LOADING TEST")
    print("=" * 70)
    
    model_name = "Qwen/Qwen2-VL-7B-Instruct"
    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    print(f"Loading model: {model_name}")
    print(f"Device: {device}")
    
    try:
        processor = AutoProcessor.from_pretrained(model_name, trust_remote_code=True)
        print("✅ Processor loaded")
        
        model = AutoModelForVision2Seq.from_pretrained(
            model_name,
            torch_dtype=torch.float16 if device == "cuda" else torch.float32,
            trust_remote_code=True
        ).to(device)
        print("✅ Model loaded")
        
        model.eval()
        print("✅ Model ready")
        return processor, model, device
        
    except Exception as e:
        print(f"❌ Model loading failed: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None
    print()

def test_simple_inference(processor, model, device):
    """Test simple text-only inference."""
    print("=" * 70)
    print("SIMPLE TEXT INFERENCE TEST")
    print("=" * 70)
    
    if processor is None or model is None:
        print("❌ Model not loaded, skipping")
        return
    
    try:
        prompt = "Hello, how are you?"
        print(f"Prompt: {prompt}")
        
        # For text-only, we'd need a tokenizer, but let's test with processor
        # Actually, let's test with vision since that's what we need
        print("⏭️  Skipping text-only test (focusing on vision)")
        
    except Exception as e:
        print(f"❌ Text inference failed: {e}")
        import traceback
        traceback.print_exc()
    print()

def test_vision_inference(processor, model, device):
    """Test vision-language inference with a simple image."""
    print("=" * 70)
    print("VISION-LANGUAGE INFERENCE TEST")
    print("=" * 70)
    
    if processor is None or model is None:
        print("❌ Model not loaded, skipping")
        return False
    
    # Find a test image
    test_image_path = REPO_ROOT / "img" / "sea_monkeys.png"
    if not test_image_path.exists():
        print(f"❌ Test image not found: {test_image_path}")
        return False
    
    try:
        print(f"Loading image: {test_image_path}")
        img = Image.open(test_image_path).convert('RGB')
        print(f"✅ Image loaded: {img.size}")
        
        # Test 1: Simple text + image (will fail - no image tokens)
        print("\n--- Test 1: Simple text + image (expected to fail) ---")
        try:
            prompt = "What do you see in this image?"
            print(f"Prompt: {prompt}")
            
            inputs = processor(
                text=prompt,
                images=[img],
                return_tensors="pt",
                padding=True
            ).to(device)
            
            print(f"Input IDs shape: {inputs['input_ids'].shape}")
            print(f"❌ No image tokens in text (expected)")
                    
        except Exception as e:
            print(f"❌ Expected failure: {e}")
            
        # Test 2: apply_chat_template then process (CORRECT APPROACH)
        print("\n--- Test 2: apply_chat_template + processor (CORRECT) ---")
        try:
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image"},  # Placeholder
                        {"type": "text", "text": "What do you see in this image?"}
                    ]
                }
            ]
            
            # Apply chat template to get text with <image> tokens
            text_with_image_tokens = processor.apply_chat_template(
                messages, 
                tokenize=False, 
                add_generation_prompt=True
            )
            
            print(f"Text with image tokens: {text_with_image_tokens[:100]}...")
            
            # Set padding side
            if hasattr(processor, 'tokenizer'):
                processor.tokenizer.padding_side = 'left'
            
            # Process text (with <image> tokens) + actual image
            inputs = processor(
                text=text_with_image_tokens,
                images=[img],
                return_tensors="pt",
                padding=True
            ).to(device)
            
            print(f"✅ Processor call succeeded")
            print(f"Input keys: {inputs.keys()}")
            
            if "input_ids" in inputs:
                input_ids = inputs["input_ids"]
                print(f"Input IDs shape: {input_ids.shape}")
                print(f"Input IDs (first 20): {input_ids[0][:20]}")
                
                # Check if image tokens are present (should be > 8 tokens now)
                if input_ids.shape[-1] > 10:
                    print(f"✅ Image tokens likely present (token count: {input_ids.shape[-1]})")
                else:
                    print(f"⚠️  Warning: Token count seems low, may still be missing image tokens")
                
                # Try to generate
                print("Attempting generation...")
                with torch.no_grad():
                    generated_ids = model.generate(
                        **inputs,
                        max_new_tokens=100,
                        do_sample=True,
                        temperature=0.7
                    )
                    
                    # Decode
                    input_token_len = input_ids.shape[-1]
                    generated_ids = generated_ids[:, input_token_len:]
                    
                    output_text = processor.batch_decode(
                        generated_ids, skip_special_tokens=True
                    )[0]
                    
                    print(f"✅ Generation successful!")
                    print(f"Response: {output_text}")
                    return True
                    
        except Exception as e:
            print(f"❌ apply_chat_template approach failed: {e}")
            import traceback
            traceback.print_exc()
            return False
                
    except Exception as e:
        print(f"❌ Vision inference failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    print()

def main():
    """Run all tests."""
    print("🧪 HuggingFace/Qwen2-VL Test Suite")
    print("=" * 70)
    print()
    
    # Test 1: GPU
    test_gpu()
    
    # Test 2: Model loading
    processor, model, device = test_model_loading()
    
    if processor is None or model is None:
        print("❌ Cannot continue without model")
        return 1
    
    # Test 3: Vision inference
    success = test_vision_inference(processor, model, device)
    
    if success:
        print("=" * 70)
        print("✅ ALL TESTS PASSED!")
        print("=" * 70)
        return 0
    else:
        print("=" * 70)
        print("❌ TESTS FAILED")
        print("=" * 70)
        return 1

if __name__ == "__main__":
    sys.exit(main())

