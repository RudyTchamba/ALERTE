#!/usr/bin/env bash
# Serve an open-weight model with an OpenAI-compatible API on a GPU machine (ITU sandbox, cloud VM).
#   bash sandbox/serve_vllm.sh                         # base model
#   LORA=sandbox/alerte-lora bash sandbox/serve_vllm.sh  # base model + ALERTE LoRA adapter
# Then on the ALERTE side:
#   ALERTE_BRAIN=llm ALERTE_LLM_BASE_URL=http://<host>:8000/v1 ALERTE_LLM_MODEL=<model or alerte> python -m alerte run cm01
set -e
MODEL=${MODEL:-Qwen/Qwen2.5-7B-Instruct}
PORT=${PORT:-8000}
pip install -q "vllm>=0.6"
if [ -n "$LORA" ]; then
  python -m vllm.entrypoints.openai.api_server --model "$MODEL" --port "$PORT" --max-model-len 8192 \
    --enable-lora --lora-modules alerte="$LORA"
else
  python -m vllm.entrypoints.openai.api_server --model "$MODEL" --port "$PORT" --max-model-len 8192
fi
