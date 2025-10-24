import os
import openai
import anthropic
import huggingface_hub
import tiktoken # Tokenizer for OpenAI GPT models
import sentencepiece # Tokenizer for LLaMA 2 model
from openai import OpenAI


MAX_TOKENS = 1000  # Max number of tokens that each model should generate

class Model:
    """
    Common interface for all chat model API providers
    """
    def __init__(self, config):
        self.config = config
        self.client = OpenAI(
            base_url=config.get("base_url", "http://127.0.0.1:8000/v1"),
            api_key=config.get("api_key", "ec528")
        )
        self.model_name = self.client.models.list().data[0].id
        print(f"Using model: {self.model_name}")


    def generate(self, system_message, new_user_message, history=[], temperature=1):
        messages = [{"role": "system", "content": system_message}]

        for user_message, assistant_response in history:
            messages.append({"role": "user", "content": user_message})
            messages.append({"role": "assistant", "content": assistant_response})

        messages.append({"role": "user", "content": new_user_message})

        stream = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=temperature,
            max_tokens=MAX_TOKENS,
            stream=True,
        )

        return stream

    def parse_completion(self, completion):
        # ✅ works with ChatCompletionChunk
        delta = completion.choices[0].delta
        if delta.content:
            return delta.content
        return None

class OpenAIModel(Model):
    """
    Interface for OpenAI's GPT models
    """
    def generate(self, system_message, new_user_message, history=[], temperature=1):
        messages = [{"role": "system", "content": system_message}]

        for user_message, assistant_response in history:
            if user_message:
                messages.append({"role": "user", "content": str(user_message)})
            if assistant_response:
                messages.append({"role": "assistant", "content": str(assistant_response)})

        messages.append({"role": "user", "content": str(new_user_message)})

        stream = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=temperature,
            max_tokens=MAX_TOKENS,
            stream=True,
        )

        return stream
    
    def parse_completion(self, completion):
        delta = completion.choices[0].delta
        if delta.content:
            return delta.content
        return None
  