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
- `Scene` - Spatial arrangements and organization
- `BackgroundKnowledge` - Contextual information and references

**All Mode** (13 dimensions - comprehensive analysis):
- All available dimensions including Core plus: `Emotion`, `ColorComposition`, `Metadata`, `AnalogicalMapping`, `OverallIntent`, `SemioticProjection`, `TargetCommunity`, `TemplateStructure`, `Toxicity`

#### Examples

```bash
# Navigate to the project directory
cd /path/to/meme-pipeline-server

# Extract Core dimensions (4 dimensions - faster, necessary for more layered dimensions)
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
   - `--mode Core`: Extracts 4 core dimensions (faster, necessary for further extraction since these are the core dimensions to be used by others)
   - `--mode All`: Extracts all 13 dimensions (comprehensive, slower)

2. **Specify Custom Dimensions**:
   - `--dimensions "Dimension1 Dimension2 ..."`: Extract only specific dimensions
   - Example: `--dimensions "VisualMaterial TextualMaterial OverallIntent"`

3. **Available Dimensions**:
   - `VisualMaterial`, `TextualMaterial`, `Emotion`, `ColorComposition`
   - `Scene`, `BackgroundKnowledge`, `Metadata`
   - `AnalogicalMapping`, `OverallIntent`, `SemioticProjection`
   - `TargetCommunity`, `TemplateStructure`, `Toxicity`

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
- `Emotion` - Emotional content and expressions
- `ColorComposition` - Color schemes and arrangements
- `Scene` - Spatial arrangements and organization
- `BackgroundKnowledge` - Contextual information and references
- `Metadata` - Technical and descriptive information
- `AnalogicalMapping` - Symbolic representations
- `OverallIntent` - Primary purpose or intention
- `SemioticProjection` - Projection of the User onto meme elements
- `TargetCommunity` - Intended audience
- `TemplateStructure` - Structural patterns
- `ToxicityAssessment` - Harmful or offensive elements

## 🔄 Reversed Pipeline

The pipeline includes a **reversed extraction order** that starts with `OverallIntent` and passes context between dimensions. This approach ensures that later dimensions have access to previously extracted information, improving accuracy and coherence.

### Reversed Pipeline Extraction Order

The reversed pipeline extracts dimensions in the following order, with each step receiving context from previous steps:

| Step | Dimension | Receives Context From |
|------|-----------|----------------------|
| 1 | **OverallIntent** | None (extracted first) |
| 2 | **TextualMaterial** | OverallIntent graph |
| 3 | **VisualMaterial** | OverallIntent graph |
| 4 | **Scene** | OverallIntent graph + VisualMaterial entities |
| 5 | **BackgroundKnowledge** | OverallIntent graph + VisualMaterial, TextualMaterial, Scene entities |
| 6 | **EmotionExpression** | OverallIntent graph + VisualMaterial, TextualMaterial, Scene, BackgroundKnowledge entities |
| 7 | **AnalogicalMapping** | OverallIntent graph + VisualMaterial, TextualMaterial, Scene, BackgroundKnowledge, EmotionExpression entities |
| 8 | **SemioticProjection** | OverallIntent graph + VisualMaterial, TextualMaterial, Scene, BackgroundKnowledge, AnalogicalMapping entities |
| 9 | **ToxicityAssessment** | OverallIntent graph + VisualMaterial, TextualMaterial, Scene, BackgroundKnowledge, EmotionExpression, AnalogicalMapping, SemioticProjection entities |
| 10 | **TargetCommunity** | OverallIntent graph + VisualMaterial, TextualMaterial, Scene, BackgroundKnowledge, AnalogicalMapping, ToxicityAssessment entities |

#### Detailed Description

1. **OverallIntent** (first - no dependencies)
   - Extracts the primary purpose or intention behind the meme
   - Generates a TTL graph that is passed to all subsequent steps

2. **TextualMaterial** (receives OverallIntent graph as context)
   - Extracts written or textual content
   - Uses the OverallIntent graph to understand the meme's purpose

3. **VisualMaterial** (receives OverallIntent graph as context)
   - Extracts visual content elements
   - Uses the OverallIntent graph to understand the meme's purpose

4. **Scene** (receives OverallIntent graph + VisualMaterial entities)
   - Extracts spatial arrangements and organization
   - Uses OverallIntent graph and VisualMaterial entities to understand scene composition

5. **BackgroundKnowledge** (receives OverallIntent graph + VisualMaterial, TextualMaterial, Scene entities)
   - Extracts contextual information and references
   - Uses OverallIntent graph and all previously extracted entities to identify background knowledge

6. **EmotionExpression** (receives OverallIntent graph + VisualMaterial, TextualMaterial, Scene, BackgroundKnowledge entities)
   - Extracts emotional content and affective dimensions
   - Uses OverallIntent graph and previously extracted entities to identify emotions

7. **AnalogicalMapping** (receives OverallIntent graph + VisualMaterial, TextualMaterial, Scene, BackgroundKnowledge, EmotionExpression entities)
   - Extracts symbolic representations and analogical mappings
   - Uses OverallIntent graph and all previously extracted entities to identify mappings

8. **SemioticProjection** (receives OverallIntent graph + VisualMaterial, TextualMaterial, Scene, BackgroundKnowledge, AnalogicalMapping entities)
   - Extracts user projections onto meme elements
   - Uses OverallIntent graph and previously extracted entities to identify semiotic projections

9. **ToxicityAssessment** (receives OverallIntent graph + VisualMaterial, TextualMaterial, Scene, BackgroundKnowledge, EmotionExpression, AnalogicalMapping, SemioticProjection entities)
   - Evaluates harmful or offensive elements
   - Uses OverallIntent graph and all previously extracted entities to assess toxicity

10. **TargetCommunity** (receives OverallIntent graph + VisualMaterial, TextualMaterial, Scene, BackgroundKnowledge, AnalogicalMapping, ToxicityAssessment entities)
    - Extracts the intended audience or community
    - Uses OverallIntent graph and previously extracted entities to identify target community

### Context Passing Mechanism

Each dimension extraction step receives:
- **OverallIntent graph**: A TTL-formatted knowledge graph containing the extracted OverallIntent dimension
- **Entity lists**: Lists of previously extracted entities from specific dimensions (e.g., VisualMaterial entities, TextualMaterial entities)

This context is included in the prompt as "In Context Material for the Meme Analysis", allowing the LLM to make more informed and coherent extractions.

### Using the Reversed Pipeline

To use the reversed pipeline, use the `extract_dimensions_reversed.py` script:

```bash
# Extract dimensions using reversed pipeline with Claude
python extract_dimensions_reversed.py img/meme.png --llm-provider claude

# Extract dimensions using reversed pipeline with HuggingFace
python extract_dimensions_reversed.py img/meme.png --llm-provider huggingface

# Specify custom output directory
python extract_dimensions_reversed.py img/meme.png --output-dir ./output_reversed
```

Or use the SLURM batch script:

```bash
# Submit job to SLURM cluster
sbatch scripts/sbatch/extract_dimensions_reversed.sbatch img/meme.png --llm-provider claude
```

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
- `Scene` - Spatial arrangements
- `BackgroundKnowledge` - Contextual information

### Example 2: Comprehensive Analysis with All Dimensions

Using the batch script with All mode for complete analysis:

```bash
# Extract all 13 dimensions from a meme
./scripts/sh/run_meme_pipeline.sh --image img/meme.png --mode All
```

This extracts all available dimensions including Core plus:
- `Emotion`, `ColorComposition`, `Metadata`
- `AnalogicalMapping`, `OverallIntent`
- `SemioticProjection`, `TargetCommunity`
- `TemplateStructure`, `Toxicity`

### Example 3: Custom Dimension Selection

Extract only specific dimensions you need:

```bash
# Extract only VisualMaterial and OverallIntent
./scripts/sh/run_meme_pipeline.sh --image img/meme.png --dimensions "VisualMaterial OverallIntent"

# Extract multiple specific dimensions
./scripts/sh/run_meme_pipeline.sh --image img/meme.png --dimensions "TextualMaterial VisualMaterial Emotion OverallIntent"
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
