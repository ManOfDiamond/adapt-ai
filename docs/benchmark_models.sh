#!/usr/bin/env bash
#
# benchmark_models.sh
#
# Runs each model in Adapt AI's catalog once, captures latency/throughput
# from `ollama run --verbose`, confirms CPU vs GPU via `ollama ps`, and
# writes a markdown table you can paste directly into
# docs/TECHNICAL_REPORT.md.
#
# Usage:
#   ./benchmark_models.sh                # benchmark every model in the catalog
#   ./benchmark_models.sh qwen2.5:0.5b mistral:7b   # benchmark only specific models
#
# Note: this will `ollama pull` any model not already present, which can be
# a multi-GB download for the larger models (llava:13b is 8GB). Pass
# specific model tags as arguments if you don't want to pull everything.

set -euo pipefail

PROMPT="Explain photosynthesis in two sentences."
OUTPUT_MD="benchmark_results.md"

DEFAULT_MODELS=(
  "qwen2.5:0.5b"
  "qwen2.5:1.5b"
  "gemma2:2b"
  "gemma3:4b"
  "phi3:mini"
  "llama3.2:1b"
  "llama3.2:3b"
  "mistral:7b"
  "llava:7b"
  "llama3.1:8b"
  #"llava:13b"
  "gemma2:9b"
  #"llama3.2-vision"
)

if [ "$#" -gt 0 ]; then
  MODELS=("$@")
else
  MODELS=("${DEFAULT_MODELS[@]}")
fi

echo "| Model | Tokens/sec | Time to first token | Processor | Notes |" > "$OUTPUT_MD"
echo "|---|---|---|---|---|" >> "$OUTPUT_MD"

for MODEL in "${MODELS[@]}"; do
  echo ""
  echo "=== Benchmarking $MODEL ==="

  if ! ollama list | grep -q "^${MODEL} "; then
    echo "Model not found locally, pulling $MODEL ..."
    if ! ollama pull "$MODEL"; then
      echo "| \`$MODEL\` | - | - | - | pull failed, skipped |" >> "$OUTPUT_MD"
      continue
    fi
  fi

  RUN_LOG=$(mktemp)
  if ! ollama run "$MODEL" "$PROMPT" --verbose > "$RUN_LOG" 2>&1; then
    echo "| \`$MODEL\` | - | - | - | run failed, skipped |" >> "$OUTPUT_MD"
    rm -f "$RUN_LOG"
    continue
  fi

  # Check processor while the model is still loaded (immediately after run,
  # no background job / loop race like the earlier manual attempt hit).
  PROCESSOR=$(ollama ps | awk -v m="$MODEL" '$1==m {for(i=1;i<=NF;i++) if ($i ~ /%/) {out=$i; if ($(i+1) ~ /^(CPU|GPU)/ && $(i+1) !~ /%/) out=out" "$(i+1); print out; exit}}')
  if [ -z "$PROCESSOR" ]; then
    PROCESSOR="unknown (model already unloaded before check)"
  fi

  LOAD_MS=$(grep "load duration:" "$RUN_LOG" | grep -oE '[0-9.]+(ms|s)' | head -1)
  PROMPT_EVAL_MS=$(grep "prompt eval duration:" "$RUN_LOG" | grep -oE '[0-9.]+(ms|s)' | head -1)
  EVAL_RATE=$(grep "eval rate:" "$RUN_LOG" | tail -1 | grep -oE '[0-9.]+ tokens/s')

  echo "| \`$MODEL\` | ${EVAL_RATE:-n/a} | load ${LOAD_MS:-n/a} + prompt-eval ${PROMPT_EVAL_MS:-n/a} | $PROCESSOR | |" >> "$OUTPUT_MD"

  rm -f "$RUN_LOG"
done

echo ""
echo "=== Done. Results written to $OUTPUT_MD ==="
cat "$OUTPUT_MD"
