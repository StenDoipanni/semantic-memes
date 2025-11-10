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

### 2. Basic Usage

```python
from pipeline import analyze_meme

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

### 3. Command Line Usage

```bash
# Analyze a single meme
python run_pipeline.py /path/to/meme.png

# Analyze with specific dimensions
python run_pipeline.py /path/to/meme.png --dimensions VisualMaterial TextualMaterial

# Batch analyze multiple memes
python run_pipeline.py /path/to/memes/ --batch

# Use specific LLM provider
python run_pipeline.py /path/to/meme.png --llm-provider claude
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

### Example 1: Basic Analysis

```python
from pipeline import analyze_meme
from pathlib import Path

result = analyze_meme(
    image_path=Path("meme.png"),
    output_dir=Path("output")
)

if result['success']:
    print(f"Found {result['summary']['dimensions_extracted']} dimensions")
    print(f"Generated {result['summary']['qa_pairs_generated']} Q&A pairs")
```

### Example 2: Custom Configuration

```python
from pipeline import MemeAnalysisPipeline

pipeline = MemeAnalysisPipeline(
    llm_provider="claude",
    output_dir=Path("custom_output")
)

result = pipeline.analyze_meme(
    image_path=Path("meme.png"),
    selected_dimensions=["OverallIntent", "VisualMaterial"],
    question_types=["descriptive", "interpretive"],
    questions_per_type=3
)
```

### Example 3: Batch Processing

```python
from pipeline import batch_analyze_memes
from pathlib import Path

image_paths = [
    Path("meme1.png"),
    Path("meme2.png"),
    Path("meme3.png")
]

results = batch_analyze_memes(
    image_paths=image_paths,
    selected_dimensions=["OverallIntent", "TextualMaterial"],
    question_types=["descriptive"],
    questions_per_type=2
)

successful = sum(1 for r in results if r['success'])
print(f"Successfully analyzed {successful}/{len(results)} memes")
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