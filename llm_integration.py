"""
LLM Integration Module.

This module provides interfaces for interacting with different Large Language Models,
including Claude API (Anthropic) and HuggingFace/vLLM for local models. It handles API calls,
error handling, retries, and response processing.
"""

import json
import logging
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import requests
from anthropic import Anthropic
from PIL import Image
import base64
import io

from config import LLMConfig, ErrorMessages

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.
    
    This class defines the interface that all LLM providers must implement,
    ensuring consistent behavior across different model types.
    """
    
    @abstractmethod
    def generate_response(
        self, 
        prompt: str, 
        image_path: Optional[Path] = None,
        **kwargs
    ) -> str:
        """
        Generate a response from the LLM.
        
        Args:
            prompt: The text prompt to send to the model
            image_path: Optional path to an image file
            **kwargs: Additional parameters specific to the provider
            
        Returns:
            Generated response text
            
        Raises:
            Exception: If the request fails
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if the LLM provider is available and configured.
        
        Returns:
            True if the provider is available, False otherwise
        """
        pass


class ClaudeProvider(LLMProvider):
    """
    Provider for Anthropic Claude API.
    
    This class handles communication with the Claude API, including
    image processing, prompt formatting, and response handling.
    """
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize the Claude provider.
        
        Args:
            api_key: Claude API key. If None, uses environment variable
            model: Claude model to use. If None, uses default from config
        """
        self.api_key = api_key or LLMConfig.CLAUDE_API_KEY
        self.model = model or LLMConfig.CLAUDE_MODEL
        self.client = None
        
        if self.api_key:
            try:
                self.client = Anthropic(api_key=self.api_key)
                logger.info("Claude provider initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Claude client: {e}")
                self.client = None
    
    def is_available(self) -> bool:
        """Check if Claude provider is available."""
        return self.client is not None and self.api_key is not None
    
    def generate_response(
        self, 
        prompt: str, 
        image_path: Optional[Path] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> str:
        """
        Generate a response using Claude API.
        
        Args:
            prompt: The text prompt
            image_path: Optional path to an image file
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional parameters
            
        Returns:
            Generated response text
            
        Raises:
            Exception: If the API call fails
        """
        if not self.is_available():
            if not self.api_key:
                raise Exception("Claude API key is not set. Please set CLAUDE_API_KEY environment variable.")
            raise Exception("Claude provider is not available. Check API key and initialization.")
        
        try:
            # Prepare the message content
            content = [{"type": "text", "text": prompt}]
            
            # Add image if provided
            if image_path and image_path.exists():
                image_data, media_type = self._process_image(image_path)
                content.insert(0, {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": image_data
                    }
                })
            
            # Prepare the request parameters
            # NOTE: Each call creates a fresh conversation with no history.
            # This ensures each dimension extraction is independent.
            request_params = {
                "model": self.model,
                "max_tokens": max_tokens or LLMConfig.CLAUDE_MAX_TOKENS,
                "temperature": temperature or LLMConfig.CLAUDE_TEMPERATURE,
                "messages": [{"role": "user", "content": content}]  # Fresh conversation, no history
            }
            
            # Make the API call with retries
            response = self._make_request_with_retries(request_params)
            
            # Extract and return the response text
            if response.content and len(response.content) > 0:
                return response.content[0].text
            else:
                raise Exception("Empty response from Claude API")
                
        except Exception as e:
            error_msg = ErrorMessages.LLM_API_ERROR.format(error=str(e))
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def _process_image(self, image_path: Path) -> tuple[str, str]:
        """
        Process and encode an image for Claude API.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Tuple of (base64 encoded image data, media type)
        """
        try:
            # Open and resize image if necessary
            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Resize if too large
                max_size = LLMConfig.CLAUDE_MAX_IMAGE_SIZE
                if img.size[0] > max_size[0] or img.size[1] > max_size[1]:
                    img.thumbnail(max_size, Image.Resampling.LANCZOS)
                
                # Convert to base64
                buffer = io.BytesIO()
                img.save(buffer, format='JPEG', quality=85)
                image_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
                
                # Return both data and correct media type (JPEG since we're saving as JPEG)
                return image_data, 'image/jpeg'
                
        except Exception as e:
            raise Exception(f"Failed to process image: {e}")
    
    def _get_media_type(self, image_path: Path) -> str:
        """
        Get the media type for an image file by detecting the actual format.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Media type string
        """
        try:
            # Use PIL to detect the actual image format
            with Image.open(image_path) as img:
                format_mapping = {
                    'JPEG': 'image/jpeg',
                    'PNG': 'image/png',
                    'WEBP': 'image/webp',
                    'GIF': 'image/gif',
                    'BMP': 'image/bmp',
                    'TIFF': 'image/tiff'
                }
                actual_format = img.format
                if actual_format in format_mapping:
                    return format_mapping[actual_format]
                else:
                    # Fallback to file extension if format not recognized
                    suffix = image_path.suffix.lower()
                    media_types = {
                        '.jpg': 'image/jpeg',
                        '.jpeg': 'image/jpeg',
                        '.png': 'image/png',
                        '.webp': 'image/webp'
                    }
                    return media_types.get(suffix, 'image/jpeg')
        except Exception as e:
            logger.warning(f"Could not detect image format for {image_path}: {e}")
            # Fallback to file extension
            suffix = image_path.suffix.lower()
            media_types = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.webp': 'image/webp'
            }
            return media_types.get(suffix, 'image/jpeg')
    
    def _make_request_with_retries(self, request_params: Dict[str, Any]) -> Any:
        """
        Make API request with retry logic.
        
        Args:
            request_params: Parameters for the API request
            
        Returns:
            API response
            
        Raises:
            Exception: If all retries fail
        """
        last_exception = None
        
        for attempt in range(LLMConfig.MAX_RETRIES):
            try:
                response = self.client.messages.create(**request_params)
                return response
                
            except Exception as e:
                last_exception = e
                error_str = str(e)
                
                # Check for authentication errors
                if "401" in error_str or "authentication" in error_str.lower() or "invalid x-api-key" in error_str.lower():
                    logger.error(f"❌ Claude API authentication failed (attempt {attempt + 1}): {e}")
                    logger.error("   This usually means:")
                    logger.error("   1. The API key is invalid or expired")
                    logger.error("   2. The API key format is incorrect")
                    logger.error("   3. The API key doesn't have the required permissions")
                    logger.error(f"   API key preview: {self.api_key[:20] if self.api_key else 'NOT SET'}...")
                    # Don't retry on authentication errors
                    raise Exception(f"Claude API authentication failed: {e}. Please check your CLAUDE_API_KEY environment variable.")
                else:
                    logger.warning(f"Claude API attempt {attempt + 1} failed: {e}")
                
                if attempt < LLMConfig.MAX_RETRIES - 1:
                    time.sleep(LLMConfig.RETRY_DELAY * (attempt + 1))
        
        raise last_exception


class HuggingFaceProvider(LLMProvider):
    """
    Provider for HuggingFace models using transformers library directly.
    
    This class handles model loading, inference, and response generation for
    both text and vision-language models, with automatic GPU support.
    """
    
    def __init__(self, model: Optional[str] = None, device: Optional[str] = None):
        """
        Initialize the HuggingFace provider.
        
        Args:
            model: HuggingFace model to use. If None, uses default from config
            device: Device to use ("cuda", "cpu", or None for auto-detection)
        """
        self.model_name = model or LLMConfig.HUGGINGFACE_MODEL
        
        # Use device from config if explicitly set, otherwise detect
        if device is not None:
            self.device = device
        elif LLMConfig.HUGGINGFACE_DEVICE is not None:
            self.device = LLMConfig.HUGGINGFACE_DEVICE
        else:
            self.device = self._detect_device()
        
        # Model components (lazy loading)
        self.processor = None
        self.model = None
        self.tokenizer = None
        self._model_loaded = False
        
        logger.info(f"HuggingFace provider initialized with model: {self.model_name}")
        logger.info(f"Device: {self.device}")
        
        # Log CUDA status
        if self.device == "cuda":
            try:
                import torch
                if torch.cuda.is_available():
                    logger.info(f"Using GPU: {torch.cuda.get_device_name(0)}")
                else:
                    logger.warning("Device set to CUDA but CUDA not available, will use CPU")
                    self.device = "cpu"
            except ImportError:
                logger.warning("PyTorch not available, using CPU")
                self.device = "cpu"
    
    def _detect_device(self) -> str:
        """Detect available device (CUDA if available, else CPU)."""
        try:
            import torch
            
            # Check if CUDA is available
            if torch.cuda.is_available():
                device_id = 0
                device_name = torch.cuda.get_device_name(device_id)
                logger.info(f"CUDA available - Device: {device_name}")
                return "cuda"
            else:
                logger.warning("CUDA not available, using CPU")
                return "cpu"
        except ImportError:
            logger.warning("PyTorch not available, defaulting to CPU")
            return "cpu"
        except Exception as e:
            logger.warning(f"Error detecting device: {e}, defaulting to CPU")
            return "cpu"
    
    def _load_model(self) -> None:
        """Lazily load the model and processor (only when first needed)."""
        if self._model_loaded:
            logger.info("Model already loaded, skipping reload")
            return
        
        try:
            from transformers import AutoProcessor, AutoTokenizer, AutoModelForCausalLM
            import torch
            
            logger.info(f"🚀 Starting to load HuggingFace model: {self.model_name} on {self.device}")
            logger.info(f"   This may take several minutes for large models like Qwen3-VL...")
            
            # Check if it's Qwen3-VL (requires Qwen3VLForConditionalGeneration)
            is_qwen3_vl = "qwen3" in self.model_name.lower() and "vl" in self.model_name.lower()
            
            # Check if it's a vision-language model
            is_vision_model = any(vl in self.model_name.lower() for vl in ["vl", "vision", "clip", "blip"])
            
            if is_qwen3_vl:
                # Qwen3-VL requires Qwen3VLForConditionalGeneration
                try:
                    from transformers import Qwen3VLForConditionalGeneration
                    logger.info("Loading Qwen3-VL model (requires Qwen3VLForConditionalGeneration)")
                    self.processor = AutoProcessor.from_pretrained(self.model_name, trust_remote_code=True)
                    self.model = Qwen3VLForConditionalGeneration.from_pretrained(
                        self.model_name,
                        torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                        device_map=self.device if self.device == "cuda" else None,
                        trust_remote_code=True
                    )
                    if self.device != "cuda":
                        self.model = self.model.to(self.device)
                    logger.info(f"Loaded Qwen3-VL model: {self.model_name}")
                except ImportError as e:
                    raise Exception(
                        "Qwen3-VL requires transformers from source. Install with: "
                        "pip install git+https://github.com/huggingface/transformers.git"
                    )
                except Exception as e:
                    raise Exception(f"Failed to load Qwen3-VL model: {e}")
            elif is_vision_model:
                # Load other vision-language models (Qwen2-VL, etc.)
                try:
                    from transformers import AutoModelForVision2Seq
                    self.processor = AutoProcessor.from_pretrained(self.model_name, trust_remote_code=True)
                    self.model = AutoModelForVision2Seq.from_pretrained(
                        self.model_name,
                        torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                        trust_remote_code=True
                    ).to(self.device)
                    logger.info(f"Loaded vision-language model: {self.model_name}")
                except Exception as e:
                    logger.warning(f"Failed to load as Vision2Seq, trying as CausalLM: {e}")
                    # Fallback to regular model loading
                    self.processor = AutoProcessor.from_pretrained(self.model_name, trust_remote_code=True)
                    self.model = AutoModelForCausalLM.from_pretrained(
                        self.model_name,
                        torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                        trust_remote_code=True
                    ).to(self.device)
            else:
                # Load text-only model
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_name, trust_remote_code=True)
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                    trust_remote_code=True
                ).to(self.device)
                logger.info(f"Loaded text model: {self.model_name}")
            
            self.model.eval()  # Set to evaluation mode
            self._model_loaded = True
            logger.info("Model loaded successfully")
            
        except ImportError as e:
            raise Exception("transformers library not installed. Install with: pip install transformers torch")
        except Exception as e:
            raise Exception(f"Failed to load HuggingFace model: {e}")
    
    def is_available(self) -> bool:
        """Check if HuggingFace provider is available."""
        try:
            import torch
            import transformers
            return True
        except ImportError:
            return False
    
    def generate_response(
        self, 
        prompt: str, 
        image_path: Optional[Path] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        Generate a response using HuggingFace transformers.
        
        Args:
            prompt: The text prompt
            image_path: Optional path to an image file (for vision-language models)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters
            
        Returns:
            Generated response text
            
        Raises:
            Exception: If generation fails
        """
        # Load model if not already loaded
        if not self._model_loaded:
            self._load_model()
        
        try:
            import torch
            
            # Check if we have a vision-language model
            if self.processor is not None and image_path is not None and image_path.exists():
                return self._generate_vision_response(prompt, image_path, temperature, max_tokens, **kwargs)
            else:
                return self._generate_text_response(prompt, temperature, max_tokens, **kwargs)
                
        except Exception as e:
            error_msg = ErrorMessages.LLM_API_ERROR.format(error=str(e))
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def _generate_vision_response(
        self,
        prompt: str,
        image_path: Path,
        temperature: Optional[float],
        max_tokens: Optional[int],
        **kwargs
    ) -> str:
        """Generate response for vision-language models (Qwen2-VL, Qwen3-VL)."""
        try:
            import torch
            
            # Process image and text for Qwen2-VL
            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Qwen2-VL/Qwen3-VL requires apply_chat_template to insert image placeholders
                # Then process the text (with image tokens) along with the actual image
                # NOTE: Each call creates a fresh conversation with no history.
                # This ensures each dimension extraction is independent.
                messages = [
                    {
                        "role": "user",
                        "content": [
                            {"type": "image"},  # Placeholder for image
                            {"type": "text", "text": prompt}
                        ]
                    }
                ]  # Fresh conversation, no history
                
                # Apply chat template - this inserts <image> tokens into the text
                text_with_image_tokens = self.processor.apply_chat_template(
                    messages, 
                    tokenize=False, 
                    add_generation_prompt=True
                )
                
                # Set padding side to left for Qwen2-VL
                if hasattr(self.processor, 'tokenizer'):
                    self.processor.tokenizer.padding_side = 'left'
                
                # Now process text (with <image> tokens) and actual image
                # The processor will match the <image> tokens with the actual image
                inputs = self.processor(
                    text=text_with_image_tokens,  # Text string with <image> tokens
                    images=[img],  # Actual PIL image
                    return_tensors="pt",
                    padding=True
                ).to(self.device)
                
                # Generate with parameters
                generate_kwargs = {
                    "max_new_tokens": max_tokens or LLMConfig.HUGGINGFACE_MAX_TOKENS,
                    "do_sample": True,
                    "temperature": temperature or LLMConfig.HUGGINGFACE_TEMPERATURE
                }
                
                # Generate
                with torch.no_grad():
                    generated_ids = self.model.generate(**inputs, **generate_kwargs)
                    
                    # Get input token length to extract only generated tokens
                    if "input_ids" in inputs:
                        input_token_len = inputs["input_ids"].shape[-1]
                        generated_ids = generated_ids[:, input_token_len:]
                    
                    # Decode output
                    output_text = self.processor.batch_decode(
                        generated_ids, skip_special_tokens=True, clean_up_tokenization_spaces=False
                    )[0]
                
                return output_text.strip()
                
        except Exception as e:
            logger.error(f"Vision generation error details: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise Exception(f"Vision generation failed: {e}")
    
    def _generate_text_response(
        self,
        prompt: str,
        temperature: Optional[float],
        max_tokens: Optional[int],
        **kwargs
    ) -> str:
        """Generate response for text-only models."""
        try:
            import torch
            
            # Tokenize input
            inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)
            
            # Generate with parameters
            generate_kwargs = {
                "max_new_tokens": max_tokens or LLMConfig.HUGGINGFACE_MAX_TOKENS,
            }
            
            if temperature is not None:
                generate_kwargs["temperature"] = temperature
                generate_kwargs["do_sample"] = True
            else:
                generate_kwargs["temperature"] = LLMConfig.HUGGINGFACE_TEMPERATURE
                generate_kwargs["do_sample"] = True
            
            # Generate
            with torch.no_grad():
                outputs = self.model.generate(**inputs, **generate_kwargs)
                output_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # Remove input prompt from output
            if output_text.startswith(prompt):
                output_text = output_text[len(prompt):].strip()
            
            return output_text
            
        except Exception as e:
            raise Exception(f"Text generation failed: {e}")
    
    def get_available_models(self) -> List[str]:
        """
        Get list of supported models (example models that work with this provider).
        
        Returns:
            List of supported model names
        """
        return [
            "Qwen/Qwen2-VL-7B-Instruct",
            "Qwen/Qwen2-VL-2B-Instruct",
            "Qwen/Qwen2.5-7B-Instruct",
            "Qwen/Qwen2.5-32B-Instruct",
        ]


class LLMManager:
    """
    Manager class for handling multiple LLM providers.
    
    This class provides a unified interface for working with different
    LLM providers and handles fallback logic.
    """
    
    def __init__(self):
        """Initialize the LLM manager with available providers."""
        self.providers = {}
        self._initialize_providers()
    
    def _initialize_providers(self) -> None:
        """Initialize available LLM providers."""
        # Initialize Claude provider
        claude_provider = ClaudeProvider()
        if claude_provider.is_available():
            self.providers["claude"] = claude_provider
            logger.info("Claude provider available")
        else:
            logger.warning("Claude provider not available")
        
        # Initialize HuggingFace/vLLM provider
        huggingface_provider = HuggingFaceProvider()
        if huggingface_provider.is_available():
            self.providers["huggingface"] = huggingface_provider
            logger.info("HuggingFace/vLLM provider available")
        else:
            logger.warning("HuggingFace/vLLM provider not available")
    
    def get_provider(self, provider_name: str) -> Optional[LLMProvider]:
        """
        Get a specific provider by name.
        
        Args:
            provider_name: Name of the provider ("claude" or "huggingface")
            
        Returns:
            Provider instance or None if not available
        """
        return self.providers.get(provider_name)
    
    def get_available_providers(self) -> List[str]:
        """
        Get list of available provider names.
        
        Returns:
            List of available provider names
        """
        return list(self.providers.keys())
    
    def generate_response(
        self, 
        prompt: str, 
        image_path: Optional[Path] = None,
        provider: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Generate a response using the specified or best available provider.
        
        Args:
            prompt: The text prompt
            image_path: Optional path to an image file
            provider: Specific provider to use ("claude" or "huggingface")
            **kwargs: Additional parameters
            
        Returns:
            Generated response text
            
        Raises:
            Exception: If no providers are available or all fail
        """
        if provider:
            if provider in self.providers:
                # Use specified provider
                logger.info(f"Using specified provider: {provider}")
                return self.providers[provider].generate_response(
                    prompt, image_path, **kwargs
                )
            else:
                logger.warning(f"Requested provider '{provider}' not found. Available: {list(self.providers.keys())}")
                # Fall through to try available providers
        
        # Try providers in order of preference
        preferred_order = ["claude", "huggingface"]
        
        for provider_name in preferred_order:
            if provider_name in self.providers:
                try:
                    logger.info(f"Trying provider: {provider_name}")
                    return self.providers[provider_name].generate_response(
                        prompt, image_path, **kwargs
                    )
                except Exception as e:
                    logger.warning(f"Provider {provider_name} failed: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                    continue
        
        raise Exception(f"No available LLM providers or all providers failed. Available: {list(self.providers.keys())}")
    
    def get_current_model(self) -> str:
        """
        Get the current model name being used.
        
        Returns:
            Model name string
        """
        # Try to get model from HuggingFace/vLLM provider first (for local inference)
        if "huggingface" in self.providers:
            huggingface_provider = self.providers["huggingface"]
            if hasattr(huggingface_provider, 'model'):
                return huggingface_provider.model
        
        # Try to get model from Claude provider
        if "claude" in self.providers:
            claude_provider = self.providers["claude"]
            if hasattr(claude_provider, 'model'):
                return claude_provider.model
        
        # Fallback to default
        return "unknown_model"


# Convenience functions
def get_llm_manager() -> LLMManager:
    """Get a configured LLM manager instance."""
    return LLMManager()


def generate_response(
    prompt: str, 
    image_path: Optional[Path] = None,
    provider: Optional[str] = None,
    **kwargs
) -> str:
    """
    Generate a response using the best available LLM provider.
    
    Args:
        prompt: The text prompt
        image_path: Optional path to an image file
        provider: Specific provider to use
        **kwargs: Additional parameters
        
    Returns:
        Generated response text
    """
    manager = get_llm_manager()
    return manager.generate_response(prompt, image_path, provider, **kwargs)


if __name__ == "__main__":
    # Example usage and testing
    logging.basicConfig(level=logging.INFO)
    
    try:
        manager = get_llm_manager()
        
        # Check available providers
        providers = manager.get_available_providers()
        print(f"Available providers: {providers}")
        
        if providers:
            # Test with a simple prompt
            prompt = "Hello, how are you?"
            response = manager.generate_response(prompt)
            print(f"Response: {response}")
        else:
            print("No LLM providers available")
            
    except Exception as e:
        print(f"Error: {e}")
