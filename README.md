# Meme Analysis Pipeline

A comprehensive pipeline for analyzing memes using Large Language Models (LLMs), Multimodal Language Models (MLMs), and Vision Language Models (VLMs) with ontological knowledge representation.

## 🏗️ Architecture Overview

The pipeline consists of two main components that mirror the architecture diagram:

1. **Dimensions Extraction Component**: Extracts structured dimensions from memes using LLMs and ontological knowledge
2. **Q&A Generation Component**: Generates questions and answers about memes based on extracted dimensions

## 📁 Project Structure

```
script/
├── config.py                 # Configuration settings and constants
├── ontology_loader.py        # OWL ontology loading and parsing
├── llm_integration.py        # LLM provider interfaces (Claude + Ollama)
├── dimensions_extractor.py   # Main dimensions extraction component
├── qa_generator.py          # Q&A generation component
├── jsonld_handler.py        # JSON-LD output formatting
├── pipeline.py              # Main pipeline orchestrator
├── run_pipeline.py          # Command-line interface
├── example_usage.py         # Usage examples
├── requirements.txt         # Python dependencies
├── .env.example            # Environment variables template
└── README.md               # This file
```

## 🚀 Quick Start

### 1. Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env with your API keys
# CLAUDE_API_KEY=your_claude_api_key_here
```

### 2. Recommended: Using Batch Scripts (Easiest Method)

**We strongly recommend using the provided batch scripts** for running the pipeline. These scripts handle environment setup, configuration, and provide convenient presets for dimension extraction.

#### Why Use Batch Scripts?

- **Automatic Environment Setup**: Handles conda environment activation and dependency checks
- **Pre-configured Settings**: Environment variables and paths are automatically set
- **Convenient Presets**: Easy-to-use "Core" and "All" dimension modes
- **Flexible Dimension Selection**: Can use presets or specify custom dimensions
- **Error Handling**: Built-in validation and helpful error messages

#### Basic Usage with Batch Scripts

The main batch script is located at `scripts/sh/run_meme_pipeline.sh`. It supports two convenient modes:

**Core Mode** (4 dimensions - recommended for quick analysis):
- `TextualMaterial` - Written or textual content
- `VisualMaterial` - Visual content elements  
- `SceneUnderstanding` - Spatial arrangements and organization
- `BackgroundKnowledge` - Contextual information and references

**All Mode** (13 dimensions - comprehensive analysis):
- All available dimensions including Core plus: `EmotionExpression`, `ColorComposition`, `Metadata`, `MetaphoricalAndAnalogicalMapping`, `OverallIntent`, `SemioticInterpretation`, `TargetCommunity`, `TemplateStructure`, `ToxicityAssessment`

#### Examples

```bash
# Navigate to the project directory
cd /path/to/meme-pipeline-server

# Extract Core dimensions (4 dimensions - faster, good for most use cases)
./scripts/sh/run_meme_pipeline.sh --image img/meme.png --mode Core

# Extract All dimensions (13 dimensions - comprehensive analysis)
./scripts/sh/run_meme_pipeline.sh --image img/meme.png --mode All

# Extract specific custom dimensions
./scripts/sh/run_meme_pipeline.sh --image img/meme.png --dimensions "VisualMaterial TextualMaterial OverallIntent"

# Use HuggingFace instead of Claude
./scripts/sh/run_meme_pipeline.sh --image img/meme.png --mode Core --llm-provider huggingface

# Specify custom output directory
./scripts/sh/run_meme_pipeline.sh --image img/meme.png --mode All --output-dir ./custom_output
```

#### Dimension Selection Options

1. **Use Preset Modes** (recommended):
   - `--mode Core`: Extracts 4 core dimensions (faster, good for most analyses)
   - `--mode All`: Extracts all 13 dimensions (comprehensive, slower)

2. **Specify Custom Dimensions**:
   - `--dimensions "Dimension1 Dimension2 ..."`: Extract only specific dimensions
   - Example: `--dimensions "VisualMaterial TextualMaterial OverallIntent"`

3. **Available Dimensions**:
   - `VisualMaterial`, `TextualMaterial`, `EmotionExpression`, `ColorComposition`
   - `SceneUnderstanding`, `BackgroundKnowledge`, `Metadata`
   - `MetaphoricalAndAnalogicalMapping`, `OverallIntent`, `SemioticInterpretation`
   - `TargetCommunity`, `TemplateStructure`, `ToxicityAssessment`

#### Batch Script Help

```bash
# View all options
./scripts/sh/run_meme_pipeline.sh --help
```

### 3. Alternative: Direct Python Usage (Advanced)

If you prefer to call Python scripts directly or need more control, you can use the Python modules directly:

```python
from pipeline import analyze_meme
from pathlib import Path

# Analyze a single meme
result = analyze_meme(
    image_path=Path("/path/to/meme.png"),
    selected_dimensions=["OverallIntent", "VisualMaterial", "TextualMaterial"],
    question_types=["descriptive", "interpretive"],
    questions_per_type=2
)

print(f"Analysis successful: {result['success']}")
print(f"Dimensions extracted: {result['summary']['dimensions_extracted']}")
print(f"Q&A pairs generated: {result['summary']['qa_pairs_generated']}")
```

Or via command line:

```bash
# Analyze a single meme
python scripts/py/run_pipeline.py /path/to/meme.png --mode dimension_extraction

# Analyze with specific dimensions
python scripts/py/run_pipeline.py /path/to/meme.png --dimensions VisualMaterial TextualMaterial

# Use specific LLM provider
python scripts/py/run_pipeline.py /path/to/meme.png --llm-provider claude
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file with the following variables:

```bash
# Claude API Configuration
CLAUDE_API_KEY=your_claude_api_key_here

# Ollama Configuration (optional)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:latest

# Pipeline Configuration
OUTPUT_DIR=./output
LOG_LEVEL=INFO
```

### Available Dimension Classes

The pipeline can extract the following dimensions from memes:

- `VisualMaterial` - Visual content elements
- `TextualMaterial` - Written or textual content
- `EmotionExpression` - Emotional content and expressions
- `ColorComposition` - Color schemes and arrangements
- `SceneUnderstanding` - Spatial arrangements and organization
- `BackgroundKnowledge` - Contextual information and references
- `Metadata` - Technical and descriptive information
- `MetaphoricalAndAnalogicalMapping` - Symbolic representations
- `OverallIntent` - Primary purpose or intention
- `SemioticInterpretation` - Signs, symbols, and meaning
- `TargetCommunity` - Intended audience
- `TemplateStructure` - Structural patterns
- `ToxicityAssessment` - Harmful or offensive elements

### Available Question Types

The pipeline can generate the following types of questions:

- `descriptive` - Factual descriptions of visible elements
- `analytical` - Analysis of relationships and patterns
- `interpretive` - Interpretation of meaning and symbolism
- `contextual` - Background knowledge and cultural context
- `evaluative` - Evaluation and assessment

## 📊 Output Formats

The pipeline generates multiple output formats:

### 1. JSON-LD Files
- **Standalone dimensions**: `{image_name}_dimensions.jsonld`
- **Standalone Q&A**: `{image_name}_qa.jsonld`
- **Unified output**: `{image_name}_unified.jsonld`

### 2. Text Files
- **Dimensions summary**: `{image_name}_dimensions.txt`
- **Q&A pairs**: `{image_name}_qa.txt`

### 3. Raw JSON Files
- **Raw dimensions data**: `{image_name}_dimensions_raw.json`
- **Raw Q&A data**: `{image_name}_qa_raw.json`

## 🔌 LLM Providers

### Claude (Anthropic)
- **Model**: claude-3-5-sonnet-20241022
- **Features**: Vision support, high-quality responses
- **Requirements**: API key

### Ollama (Local)
- **Models**: llama3.2:latest (configurable)
- **Features**: Local processing, no API costs
- **Requirements**: Ollama installed locally

## 📝 Usage Examples

### Example 1: Quick Analysis with Core Dimensions (Recommended)

Using the batch script with Core mode for fast analysis:

```bash
# Extract 4 core dimensions from a meme
./scripts/sh/run_meme_pipeline.sh --image img/meme.png --mode Core
```

This extracts:
- `TextualMaterial` - Written or textual content
- `VisualMaterial` - Visual content elements
- `SceneUnderstanding` - Spatial arrangements
- `BackgroundKnowledge` - Contextual information

### Example 2: Comprehensive Analysis with All Dimensions

Using the batch script with All mode for complete analysis:

```bash
# Extract all 13 dimensions from a meme
./scripts/sh/run_meme_pipeline.sh --image img/meme.png --mode All
```

This extracts all available dimensions including Core plus:
- `EmotionExpression`, `ColorComposition`, `Metadata`
- `MetaphoricalAndAnalogicalMapping`, `OverallIntent`
- `SemioticInterpretation`, `TargetCommunity`
- `TemplateStructure`, `ToxicityAssessment`

### Example 3: Custom Dimension Selection

Extract only specific dimensions you need:

```bash
# Extract only VisualMaterial and OverallIntent
./scripts/sh/run_meme_pipeline.sh --image img/meme.png --dimensions "VisualMaterial OverallIntent"

# Extract multiple specific dimensions
./scripts/sh/run_meme_pipeline.sh --image img/meme.png --dimensions "TextualMaterial VisualMaterial EmotionExpression OverallIntent"
```

### Example 4: Using Different LLM Providers

```bash
# Use Claude (default, recommended for best quality)
./scripts/sh/run_meme_pipeline.sh --image img/meme.png --mode Core --llm-provider claude

# Use HuggingFace (local, requires GPU)
./scripts/sh/run_meme_pipeline.sh --image img/meme.png --mode Core --llm-provider huggingface
```

### Example 5: Custom Output Directory

```bash
# Save output to a custom directory
./scripts/sh/run_meme_pipeline.sh --image img/meme.png --mode All --output-dir ./results/analysis_001
```

### Example 6: Direct Python Usage (Advanced)

If you need programmatic control:

```python
from pipeline import analyze_meme
from pathlib import Path

result = analyze_meme(
    image_path=Path("meme.png"),
    selected_dimensions=["OverallIntent", "VisualMaterial"],
    question_types=["descriptive", "interpretive"],
    questions_per_type=2
)

if result['success']:
    print(f"Found {result['summary']['dimensions_extracted']} dimensions")
    print(f"Generated {result['summary']['qa_pairs_generated']} Q&A pairs")
```

## 🛠️ Advanced Usage

### Custom Ontology

```python
from ontology_loader import OntologyLoader

# Load custom ontology
loader = OntologyLoader(Path("custom_ontology.ttl"))

# Get available dimension classes
classes = loader.get_dimension_classes()
print(f"Available classes: {[c['name'] for c in classes]}")
```

### Custom LLM Configuration

```python
from llm_integration import ClaudeProvider, OllamaProvider

# Custom Claude configuration
claude = ClaudeProvider(
    api_key="your_key",
    model="claude-3-opus-20240229"
)

# Custom Ollama configuration
ollama = OllamaProvider(
    base_url="http://localhost:11434",
    model="llama3.1:latest"
)
```

### JSON-LD Customization

```python
from jsonld_handler import JSONLDHandler

# Custom context
custom_context = {
    "@vocab": "http://example.org/custom#",
    "custom": "http://example.org/custom#"
}

handler = JSONLDHandler(custom_context)
```

## 🐛 Troubleshooting

### Common Issues

1. **Claude API Key Not Found**
   ```
   Error: Claude provider is not available
   ```
   - Solution: Set `CLAUDE_API_KEY` in your `.env` file

2. **Ollama Not Running**
   ```
   Error: Ollama provider is not available
   ```
   - Solution: Start Ollama service: `ollama serve`

3. **Image Format Not Supported**
   ```
   Error: Unsupported image format
   ```
   - Solution: Use supported formats: `.png`, `.jpg`, `.jpeg`, `.webp`

4. **Ontology Loading Failed**
   ```
   Error: Failed to load ontology
   ```
   - Solution: Check ontology file path and format

### Debug Mode

Enable verbose logging for debugging:

```bash
python run_pipeline.py /path/to/meme.png --verbose --log-file debug.log
```

## 📚 API Reference

### Main Classes

- `MemeAnalysisPipeline`: Main pipeline orchestrator
- `DimensionsExtractor`: Dimensions extraction component
- `QAGenerator`: Q&A generation component
- `OntologyLoader`: Ontology loading and parsing
- `LLMManager`: LLM provider management
- `JSONLDHandler`: JSON-LD output handling

### Key Functions

- `analyze_meme()`: Analyze a single meme
- `batch_analyze_memes()`: Analyze multiple memes
- `extract_dimensions_from_image()`: Extract dimensions only
- `generate_qa_for_image()`: Generate Q&A only

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Anthropic for Claude API
- Ollama for local LLM support
- RDFLib for ontology processing
- The meme analysis research community