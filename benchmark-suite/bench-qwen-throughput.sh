#!/usr/bin/bash

# The name of your model on the Hugging Face Hub
model_name="Qwen/Qwen1.5-MoE-A2.7B-Chat"

# The directory where the result file will be saved
result_dir=$1

# Check if a result directory was provided
if [ -z "$result_dir" ]; then
    echo "Usage: ./bench-qwen-throughput.sh <result-directory-name>"
    exit 1
fi

# Create the result directory if it doesn't exist
mkdir -p "$result_dir"

echo "Starting local throughput benchmark for: $model_name"

vllm bench throughput \
    --dataset-name random \
    --num-prompts 1024 \
    --model "$model_name" \
    --input-len 32 \
    --output-len 512 \
    --output-json "$result_dir/throughput.json"

echo "Benchmark complete. Results saved to $result_dir/throughput.json"
