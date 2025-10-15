#!/usr/bin/bash
set -euo pipefail
local_model_path="/data/Qwen1.5-MoE-A2.7B-Chat"

# make sure port 8000 is free (same as teammate)
fuser -k 8000/tcp 2>/dev/null || true

vllm bench serve \
  --port 8000 \
  --backend openai-chat \
  --dataset-name random \
  --num-prompts 1024 \
  --random-input-len 32 \
  --random-output-len 512 \
  --endpoint /v1/chat/completions \
  --model "$local_model_path" \
  --save-result \
  --result-dir "$1"

