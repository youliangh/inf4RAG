#!/usr/bin/bash

local_model_path="/data/Meta-Llama-3-8B-Instruct"

vllm bench throughput \
	--dataset-name random \
	--num-prompts 1024 \
	--model $local_model_path \
	--input-len 32 \
	--output-len 512 \
        --output-json $1/throughput.json	
