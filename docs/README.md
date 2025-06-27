# Structured Semiotic Image Analysis with Ollama and Gemma3:12b

This project provides advanced image analysis using Ollama with the Gemma3:12b model, implementing Greimas' plastic semiotics with PropBank semantic roles for detailed visual content analysis.

## Prerequisites

1. **Ollama installed and running**
   - Install Ollama from [https://ollama.ai](https://ollama.ai)
   - Start the Ollama service: `ollama serve`

2. **Gemma3:12b model pulled**
   ```bash
   ollama pull gemma3:12b
   ```

3. **Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## Folder Structure

- `scripts/` — All analysis and batch scripts (Python and shell)
- `img/` — Images to analyze
- `outputs/` — All output folders and files
- `schemas/` — JSON schema and batch config files
- `prompts/` — Prompt templates
- `docs/` — Documentation

## Analysis Modes & Terminal Commands

### 1. Simple Image Analysis (console output only)
```bash
cd scripts
./analyze_simple.sh batman-robin-global-warming.png
```

### 2. Basic Semiotic Analysis (simple JSON-LD)
```bash
cd scripts
./analyze_basic.sh batman-robin-global-warming.png "Batman slapping Robin"
```

### 3. Advanced Semiotic Analysis (structured JSON, PropBank roles, schema validation)
```bash
cd scripts
./analyze_advanced.sh batman-robin-global-warming.png "Batman and Robin are discussing global warming"
```

### 4. Advanced Analysis with JSON-LD Output
```bash
cd scripts
./analyze_advanced.sh batman-robin-global-warming.png "Batman and Robin are discussing global warming" --json-ld
```

### 5. Batch Analysis (multiple images)
```bash
cd scripts
./analyze_batch.sh ../schemas/batch_config.json
```

### 6. Direct Python Usage (from scripts/)
```bash
# Simple
python simple_image_analyzer.py batman-robin-global-warming.png
# Basic
python basic_semiotic_analyzer.py batman-robin-global-warming.png "Batman slapping Robin"
# Advanced (structured JSON)
python advanced_semiotic_analyzer.py batman-robin-global-warming.png "Batman and Robin are discussing global warming"
# Advanced (JSON-LD)
python advanced_semiotic_analyzer.py batman-robin-global-warming.png "Batman and Robin are discussing global warming" --json-ld
# Batch
python batch_semiotic_analyzer.py ../schemas/batch_config.json
```

## Batch Config Example
```json
{
  "images": [
    {
      "path": "batman-robin-global-warming.png",
      "fact_statement": "Batman and Robin are discussing global warming."
    },
    {
      "path": "UNO_draw_25_cards.png",
      "fact_statement": "A UNO card game says to be popular or to draw 25 cards. A guy is shown with many UNO cards in his hand."
    },
    {
      "path": "disaster_girl.png",
      "fact_statement": "A girl is staring at the observer while a house is on fire in the background."
    }
  ],
  "schema_path": "schemas/semiotic_schema.json",
  "prompt_path": "prompts/structured_semiotic_prompt.txt"
}
```

## Output Structure

- **Simple**: Console output only
- **Basic**: `outputs/entailment_analysis_<image>_step1_semiotics.json`
- **Advanced (structured)**: `outputs/analysis_<image>/` (multiple files)
- **Advanced (JSON-LD)**: `outputs/structured_entailment_analysis_<image>_step1_semiotics_<timestamp>.json`
- **Batch**: `outputs/analysis_<image>/` for each image, plus `batch_summary.json`

## Troubleshooting

- **Schema/Prompt not found**: Ensure paths in config and scripts are correct (relative to project root)
- **Image file not found**: Place images in `img/` or provide full/relative path
- **Ollama/model errors**: Ensure Ollama is running and model is pulled

## Customization
- **Schema**: Edit `schemas/semiotic_schema.json`
- **Prompt**: Edit `prompts/structured_semiotic_prompt.txt`
- **Batch config**: Edit `schemas/batch_config.json`

## File Overview
- `scripts/advanced_semiotic_analyzer.py` — Advanced analysis (structured/JSON-LD)
- `scripts/basic_semiotic_analyzer.py` — Basic JSON-LD analysis
- `scripts/simple_image_analyzer.py` — Simple console analysis
- `scripts/batch_semiotic_analyzer.py` — Batch processing
- `scripts/analyze_advanced.sh` — Advanced analysis wrapper
- `scripts/analyze_basic.sh` — Basic analysis wrapper
- `scripts/analyze_simple.sh` — Simple analysis wrapper
- `scripts/analyze_batch.sh` — Batch analysis wrapper
- `schemas/semiotic_schema.json` — Output schema
- `prompts/structured_semiotic_prompt.txt` — Prompt template

---

For more details, see the comments in each script or open an issue in this repository. 