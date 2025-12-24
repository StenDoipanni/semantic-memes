#!/bin/bash
#
# Batch Dimension Extraction (Reversed Pipeline + Refinement)
# Iterates over all images in a directory and runs the extraction script

set -euo pipefail

INPUT_DIR="${1:-/home/stefano/memes/semantic-memes/img/hateful-memes-img}"
OUTPUT_DIR="${OUTPUT_DIR:-./output_reversed/hateful-memes-out}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

EXTRACTION_CMD_BASE="./scripts/sh/extract_dimensions_reversed.sh"
KB1="prompts/dimension-extraction-prompts-refined/Qua-EntitiesKnowledgeBase.jsonld"
KB2="prompts/dimension-extraction-prompts-refined/AdditionalKnowledgeBase.jsonld"

echo "🚀 Batch extraction (reversed + refine)"
echo "Input dir : $INPUT_DIR"
echo "Output dir: $OUTPUT_DIR"
echo ""

cd "$REPO_ROOT"
mkdir -p "$OUTPUT_DIR"

# Self-background with nohup unless explicitly requested to stay foreground
if [[ -z "${RUN_IN_FOREGROUND:-}" && -z "${__BATCH_NOHUP_SELF:-}" ]]; then
  LOG_FILE="${LOG_FILE:-$OUTPUT_DIR/batch_extract_folder.log}"
  export __BATCH_NOHUP_SELF=1
  echo "ℹ️  Re-executing under nohup for resiliency (log: $LOG_FILE)"
  nohup "$0" "$@" >/dev/null 2>>"$LOG_FILE" &
  echo "✅ Started in background. PID: $!"
  echo "   Tail logs with: tail -f \"$LOG_FILE\""
  exit 0
fi

# Encourage model/cache reuse (pre-download & reuse weights)
export HF_HOME="${HF_HOME:-$REPO_ROOT/.cache/huggingface}"
export TRANSFORMERS_CACHE="${TRANSFORMERS_CACHE:-$HF_HOME}"
export HF_DATASETS_CACHE="${HF_DATASETS_CACHE:-$HF_HOME}"

shopt -s nullglob
files=("$INPUT_DIR"/*.png "$INPUT_DIR"/*.jpg "$INPUT_DIR"/*.jpeg "$INPUT_DIR"/*.gif "$INPUT_DIR"/*.webp)
shopt -u nullglob

if [ ${#files[@]} -eq 0 ]; then
  echo "⚠️  No images found in $INPUT_DIR"
  exit 0
fi

total=${#files[@]}
idx=0

for img in "${files[@]}"; do
  idx=$((idx + 1))
  base="$(basename "$img")"
  name_no_ext="${base%.*}"
  out_ttl="$OUTPUT_DIR/${name_no_ext}_enhanced_ontology_reversed.ttl"
  refined_ttl="$OUTPUT_DIR/${name_no_ext}_refined_ontology.ttl"

  echo ""
  echo "📸 Processing $base ($idx/$total)"

  # Skip if output already exists
  if [ -f "$refined_ttl" ]; then
    sz=$(stat -c%s "$refined_ttl" 2>/dev/null || stat -f%z "$refined_ttl" 2>/dev/null || echo "?")
    echo "   ⏭️  Skipping (already processed): $refined_ttl ($sz bytes)"
    continue
  fi

  cmd="$EXTRACTION_CMD_BASE \"$img\" \
    --additional-kb \"$KB1\" \
    --additional-kb \"$KB2\" \
    --iterative-kb true \
    --llm-provider huggingface \
    --refine true \
    --output-dir \"$OUTPUT_DIR\""

  # shellcheck disable=SC2086
  eval $cmd

  # Show per-image output presence and size
  if [ -f "$refined_ttl" ]; then
    sz=$(stat -c%s "$refined_ttl" 2>/dev/null || stat -f%z "$refined_ttl" 2>/dev/null || echo "?")
    echo "   ✅ Refined TTL: $refined_ttl ($sz bytes)"
  elif [ -f "$out_ttl" ]; then
    sz=$(stat -c%s "$out_ttl" 2>/dev/null || stat -f%z "$out_ttl" 2>/dev/null || echo "?")
    echo "   ⚠️  Refined TTL missing, enhanced TTL found: $out_ttl ($sz bytes)"
  else
    echo "   ❌ No TTL output found for $base"
  fi
done

echo ""
echo "✅ Batch extraction completed"

