#!/usr/bin/bash

local_model_path="/data/Meta-Llama-3-8B-Instruct"

vllm bench serve \
        --port 8000 \
        --backend openai-chat \
        --dataset-name random \
        --num-prompts 1024 \
        --random-input-len 32 \
        --random-output-len 512 \
	--endpoint /v1/chat/completions \
	--model $local_model_path \
        --save-result \
	--result-dir $1
