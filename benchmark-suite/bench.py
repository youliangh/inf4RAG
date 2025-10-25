#!/usr/bin/env python3
import os
import copy
import requests
import click

vllm_bench_serve_template = \
""" 
vllm bench serve \\\n\
    --backend openai-chat \\\n\
    --dataset-name random \\\n\
    --model {model_name} \\\n\
    --num-prompts {num_prompts} \\\n\
    --random-input-len {prefill_size} \\\n\
    --random-output-len {max_sequence_length} \\\n\
    --host {host} \\\n\
    --port {port} \\\n\
    --num-warmups 32 \\\n\
    --endpoint /v1/chat/completions \\
"""


def fetch_model_name(base_url: str) -> str:
    """Fetch the available model names from the server."""
    url = f"{base_url}/models"
    response = requests.get(url)
    response.raise_for_status()
    models = response.json().get("data", [])
    if not models:
        raise ValueError("No models available from the server.")
    return models[0]["id"]


class BenchmarkConfig:
    def __init__(self, 
                 num_prompts: int,
                 prefill_size: int,
                 max_sequence_length: int,
                 host: str, port: int):
        self.num_prompts = num_prompts
        self.prefill_size = prefill_size
        self.max_sequence_length = max_sequence_length
        self.host = host
        self.port = port

        self.base_url = f"{self.host}:{self.port}/v1"
        self.model_name = "MOCK"  # fetch_model_name(self.base_url)

        self.additional_args = {}

    def add_new_arguments(self, **kwargs):
        for key, value in kwargs.items():
            self.additional_args[key] = value
    
    def get_command(self):
        basic_command = vllm_bench_serve_template.format(
            model_name=self.model_name,
            num_prompts=self.num_prompts,
            prefill_size=self.prefill_size,
            max_sequence_length=self.max_sequence_length,
            host=self.host,
            port=self.port
        )

        full_command = basic_command
        for key, value in self.additional_args.items():
            full_command += f"    --{key.replace('_', '-')} {value} \\\n"

        full_command = full_command.rstrip(" \\\n")  # Remove trailing backslash and newline

        return full_command


@click.group()
@click.option("--num-prompts", type=int, default=1024, help="Number of prompts to generate")
@click.option("--prefill-size", type=int, default=32, help="Size of prefill in tokens")
@click.option("--max-sequence-length", type=int, default=512, help="Max sequence length in tokens")
@click.option("--host", type=str, default="http://127.0.0.1", help="Host URL of the model server")
@click.option("--port", type=int, default=8000, help="Port of the model server")
@click.pass_context
def bench(ctx, num_prompts, prefill_size, max_sequence_length, host, port):
    ctx.obj = BenchmarkConfig(num_prompts, prefill_size, max_sequence_length, host, port)


@bench.command("steady")
@click.option("--duration", type=int, default=90, help="Duration of the steady benchmark in seconds")
@click.option("--rps", type=int, default=16, help="Requests per second")
@click.pass_obj
def steady_testing(config: BenchmarkConfig, **kwargs):
    inner_config = copy.deepcopy(config)
    inner_config.add_new_arguments(**kwargs)
    print(inner_config.get_command())

@bench.command("flood")
@click.option("--burstiness", type=float, default=1.0, help="Burstiness factor for flood testing")
@click.pass_obj
def flood_testing(config: BenchmarkConfig, **kwargs):
    inner_config = copy.deepcopy(config)
    inner_config.add_new_arguments(**kwargs)
    print(inner_config.get_command())

if __name__=="__main__":
    bench()

