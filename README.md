# Meme Semiotic Analysis Project

A comprehensive image analysis system using Ollama's Gemma3:12b model with Greimas' plastic semiotics and PropBank roles for structured semantic analysis.

## 🎯 Project Overview

This project provides multiple levels of image analysis complexity:
- **Simple Analysis**: Basic image description
- **Basic Semiotic Analysis**: Greimas' plastic semiotics framework
- **Advanced Semiotic Analysis**: Full structured analysis with schema validation
- **Batch Processing**: Automated analysis of multiple images

## 📁 Project Structure

```
memes/
├── scripts/                    # Python analysis scripts
│   ├── simple_image_analyzer.py
│   ├── basic_semiotic_analyzer.py
│   ├── advanced_semiotic_analyzer.py
│   ├── batch_semiotic_analyzer.py
│   └── test_semiotic_analysis.py
├── shell_wrappers/            # Shell scripts for easy execution
│   ├── analyze_simple.sh
│   ├── analyze_basic.sh
│   ├── analyze_advanced.sh
│   └── analyze_batch.sh
├── schemas/                   # JSON schemas for validation
│   ├── semiotic_schema.json
│   └── batch_config.json
├── prompts/                   # Prompt templates
│   ├── simple_prompt.txt
│   ├── basic_semiotic_prompt.txt
│   └── structured_semiotic_prompt.txt
├── img/                       # Input images
├── outputs/                   # Analysis results
└── docs/                      # Documentation
```

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Ollama with Gemma3:12b model installed
- Required Python packages (see requirements.txt)

### Installation
```bash
# Clone the repository
git clone <your-repo-url>
cd memes

# Install dependencies
pip install -r requirements.txt

# Ensure Ollama is running with Gemma3:12b
ollama run gemma3:12b
```

### Basic Usage

#### Single Image Analysis
```bash
# Simple analysis
./scripts/analyze_simple.sh img/your_image.png

# Basic semiotic analysis
./scripts/analyze_basic.sh img/your_image.png "Your fact statement"

# Advanced structured analysis
./scripts/analyze_advanced.sh img/your_image.png "Your fact statement"
```

#### Batch Analysis
```bash
# Run batch analysis
./scripts/analyze_batch.sh schemas/batch_config.json
```

## 🔧 Configuration

### Batch Configuration
Edit `schemas/batch_config.json` to configure batch processing:

```json
{
  "images": [
    {
      "image_path": "img/image1.png",
      "fact_statement": "Description of image1"
    }
  ],
  "schema_path": "schemas/semiotic_schema.json",
  "prompt_path": "prompts/structured_semiotic_prompt.txt",
  "output_dir": "outputs/batch_analysis"
}
```

## 📊 Analysis Types

### 1. Simple Analysis
- Basic image description
- No structured output
- Fastest processing

### 2. Basic Semiotic Analysis
- Greimas' plastic semiotics framework
- Topology, eidetic, and chromatic analysis
- JSON output with basic structure

### 3. Advanced Semiotic Analysis
- Full structured analysis with schema validation
- PropBank role integration
- Semantic relations and entailment analysis
- Flexible schema handling with `extraSchemaRelations`

### 4. Batch Processing
- Automated analysis of multiple images
- Timing information and progress tracking
- Comprehensive error handling
- Batch summary with statistics

## 🎨 Analysis Framework

### Greimas' Plastic Semiotics
- **Topology**: Spatial organization and focal points
- **Eidetic**: Shapes, lines, and contours
- **Chromatic**: Color analysis and harmony

### PropBank Roles
- **COM**: Communication
- **LOC**: Location
- **GOL**: Goal
- **PRP**: Purpose
- And more semantic roles

## 📈 Performance

Typical analysis times (Gemma3:12b):
- **Simple**: ~15-20 seconds
- **Basic**: ~20-25 seconds  
- **Advanced**: ~25-30 seconds
- **Batch**: Varies by number of images

## 🔍 Output Examples

### Structured Analysis Output
```json
{
  "metadata": {
    "analysisId": "uuid",
    "imagePath": "img/image.png",
    "factStatement": "Description",
    "analysisTime": "25.73 seconds"
  },
  "semioticAnalysis": {
    "topology": { ... },
    "eidetic": { ... },
    "chromatic": { ... }
  },
  "semanticRelations": {
    "relationships": [ ... ],
    "extraSchemaRelations": [ ... ]
  }
}
```

## 🛠️ Development

### Adding New Analysis Types
1. Create new Python script in `scripts/`
2. Add corresponding shell wrapper
3. Update schemas if needed
4. Test with sample images

### Schema Validation
The system uses JSON Schema validation with flexible handling:
- Valid relations go to `relationships`
- Invalid relations are moved to `extraSchemaRelations`
- Analysis continues even with schema mismatches

## 📝 License

[Add your license information here]

## 🤝 Contributing

[Add contribution guidelines here]

## 📞 Support

[Add contact information here] 