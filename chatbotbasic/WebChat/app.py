# app.py
import re
import datetime
import gradio as gr
import yaml

from models import OpenAIModel, AnthropicModel, HuggingFaceLlama2Model
from tools import Tools
from rag import rag_answer, rag_answer_multi 

SYSTEM_MESSAGE_TEMPLATE = "prompt.txt"

# Quick-pick repos
KNOWN_REPOS = [
    "https://github.com/EC528-Fall-2025/inf4RAG",
    "https://github.com/EC528-Fall-2025/Kagenti-AIWorkloads",
    "https://github.com/EC528-Fall-2025/Viz-TrinoFed",
    "https://github.com/EC528-Fall-2025/FedMed-ChRIS",
    "https://github.com/EC528-Fall-2025/PolicySynth-OPA",
    "https://github.com/EC528-Fall-2025/DB-LogAnalyzer",
    "https://github.com/EC528-Fall-2025/AutoSec-Certs",
    "https://github.com/EC528-Fall-2025/XFault-ITBench",
    "https://github.com/EC528-Fall-2025/CNFS-Interposer",
    "https://github.com/EC528-Fall-2025/CloudNeuro-Tekton"
]
ALL_SENTINEL = "__ALL__"  

MODELS = {
    "GPT-3.5": OpenAIModel("gpt-3.5-turbo-16k", 16384),
    "GPT-4": OpenAIModel("gpt-4", 8192),
    "Claude 2": AnthropicModel("claude-2", 100000),
    "Llama 2": HuggingFaceLlama2Model("meta-llama/Llama-2-70b-chat-hf", 4096),
}

with open("config.yaml", "r") as config_file:
    config = yaml.safe_load(config_file)

verbose = config["verbose"]
description = config["description"]
examples = config["examples"]
enabled_models = config["enabled_models"]
selected_model = enabled_models[0]
enabled_browsers = config["enabled_browsers"]
selected_browser = enabled_browsers[0]
temperature = config["temperature"]
max_actions = config["max_actions"]

llm_tools = Tools(browser=selected_browser)

def create_system_message():
    with open(SYSTEM_MESSAGE_TEMPLATE) as f:
        message = f.read()
    now = datetime.datetime.now()
    current_date = now.strftime("%B %d, %Y")
    message = message.replace("{{CURRENT_DATE}}", current_date)
    message = message.replace("{{TOOLS_PROMPT}}", llm_tools.get_tool_list_for_prompt())
    return message

def _resolve_repo(chosen_repo: str | None, typed_repo: str | None) -> str:
    """
    Returns one of:
      - "" (no RAG)
      - ALL_SENTINEL (search all known repos)
      - a specific repo URL (string)
    """
    chosen_repo = (chosen_repo or "").strip()
    typed_repo = (typed_repo or "").strip()
    if chosen_repo == "All known repos":
        return ALL_SENTINEL
    return chosen_repo if chosen_repo else typed_repo

def generate(new_user_message, history, chosen_repo=None, typed_repo=None):
    """
    If a GitHub repo is selected/typed, answer via RAG first.
    If 'All known repos' is selected, search across all KNOWN_REPOS.
    Otherwise, run the normal tool-using loop.
    """
    ACTION_REGEX = r'(\n|^)Action: (.*)\[(.*)\]'
    CONCLUSION_REGEX = r'(\n|^)Conclusion: .*'

    repo_resolved = _resolve_repo(chosen_repo, typed_repo)

    # 0) RAG path(s)
    if repo_resolved:
        try:
            if repo_resolved == ALL_SENTINEL:
                rag_resp = rag_answer_multi(KNOWN_REPOS, str(new_user_message), chat_history=history or [])
            else:
                rag_resp = rag_answer(repo_resolved, str(new_user_message), chat_history=history or [])

            if rag_resp and rag_resp.strip():
                yield rag_resp
                return
            else:
                yield "RAG returned no content; falling back to normal reasoning…"
        except Exception as e:
            yield f"RAG error: {e}\nFalling back to normal reasoning…"

    # 1) Normal agent/tool loop
    prompt = f"Question: {new_user_message}\n\n"
    full_response = ""
    iteration = 1

    model = MODELS[selected_model]
    system_message_token_count = model.count_tokens(system_message)

    try:
        while True:
            if verbose:
                print("======\nPROMPT\n======")
                print(prompt)

            stream = model.generate(
                system_message,
                prompt,
                history=history,
                temperature=temperature
            )

            partial_response = ""

            for chunk in stream:
                completion = model.parse_completion(chunk)
                if completion:
                    full_response += completion
                    partial_response += completion
                    yield full_response

                    matches = re.search(ACTION_REGEX, partial_response)
                    if matches:
                        tool = matches.group(2).strip()
                        params = matches.group(3).strip()

                        result = llm_tools.run_tool(tool, params)

                        prompt = f"Question: {new_user_message}\n\n"
                        prompt += f"{full_response}\n\n"

                        # token budgeting
                        history_token_count = 0
                        for user_message, assistant_response in history:
                            if user_message:
                                history_token_count += model.count_tokens(user_message)
                            if assistant_response:
                                history_token_count += model.count_tokens(assistant_response)

                        prompt_token_count = model.count_tokens(prompt)
                        result_token_count = model.count_tokens(result)
                        available_tokens = int(
                            0.9 * (model.context_size - system_message_token_count - history_token_count - prompt_token_count)
                        )

                        if result_token_count > available_tokens and available_tokens > 0:
                            ratio = available_tokens / result_token_count
                            truncate_result_len = int(len(result) * ratio)
                            result = result[:max(truncate_result_len, 0)]
                            full_response += (
                                f"\n\n<span style='color:gray'>*Note: Only {ratio*100:.0f}% of the "
                                f"tool result was shown to the model due to context limits.*</span>\n\n"
                            )
                            yield full_response

                        prompt += f"Result: {result}\n\n"
                        break

            if re.search(CONCLUSION_REGEX, partial_response) or not re.search(ACTION_REGEX, partial_response):
                return

            if not partial_response.endswith("\n"):
                full_response += "\n\n"
                yield full_response

            if iteration >= max_actions:
                full_response += f"<span style='color:red'>*Stopping after running {max_actions} actions.*</span>"
                yield full_response
                return
            else:
                iteration += 1

    except Exception as e:
        full_response += f"\n<span style='color:red'>Error: {e}</span>"
        yield full_response


# Create Gradio app
system_message = create_system_message()
if verbose:
    print("==============\nSYSTEM MESSAGE\n==============")
    print(system_message)

CSS = """
h1 { text-align: center; }
h3 { text-align: center; }
.contain { display: flex; flex-direction: column; }
.gradio-container { height: 100vh !important; }
#component-0 { flex-grow: 1; overflow: auto; }
#chatbot { flex-grow: 1; overflow: auto; }
"""

multiple_models_enabled = len(enabled_models) > 1
multiple_browsers_enabled = len(enabled_browsers) > 1

with gr.Blocks(css=CSS) as app:
    gr.Markdown(description)

    # Pass BOTH inputs directly to generate()
    with gr.Row():
        known_repo_dd = gr.Dropdown(
            label="Known GitHub repos",
            choices=["", "All known repos"] + KNOWN_REPOS,
            value="",
        )
        repo_url_box = gr.Textbox(
            label="(Optional) GitHub repo URL for RAG (overrides blank dropdown)",
            placeholder="https://github.com/owner/repo"
        )

    # Normalize examples for ChatInterface with additional_inputs=[known_repo_dd, repo_url_box]
    def _norm_examples(examples_list, default_repo=""):
        if not examples_list:
            return None
        if not isinstance(examples_list[0], list):
            # make each example: [prompt, known_repo, typed_repo]
            return [[ex, default_repo, ""] for ex in examples_list]
        norm = []
        for row in examples_list:
            # row could be [prompt] or [prompt, repo]
            if len(row) == 1:
                norm.append([row[0], default_repo, ""])
            elif len(row) >= 2:
                # treat row[1] as known_repo, keep typed empty
                norm.append([row[0], row[1], ""])
        return norm

    normalized_examples = _norm_examples(examples, default_repo="")  # leave blank by default

    chatinterface = gr.ChatInterface(
        fn=generate,                       # generate(msg, history, known_repo_choice, typed_repo_url)
        additional_inputs=[known_repo_dd, repo_url_box],
        examples=normalized_examples
    )

    try:
        chatinterface.chatbot.elem_id = "chatbot"
    except Exception:
        pass

    with gr.Accordion(label="Options", open=multiple_models_enabled):
        with gr.Row():
            model_selector = gr.Radio(
                label="Model",
                choices=enabled_models,
                value=selected_model,
                visible=multiple_models_enabled
            )
            browser_selector = gr.Radio(
                label="Web Browser",
                choices=enabled_browsers,
                value=selected_browser,
                visible=multiple_browsers_enabled
            )
            temperature_slider = gr.Slider(
                label="Temperature", minimum=0.1, maximum=1, step=0.1, value=temperature
            )

    def change_model(new_model):
        global selected_model
        selected_model = new_model

    def change_browser(new_browser):
        global selected_browser, llm_tools
        selected_browser = new_browser
        llm_tools.set_browser(selected_browser)

    def change_temperature(new_temperature):
        global temperature
        temperature = new_temperature

    model_selector.change(fn=change_model, inputs=model_selector)
    browser_selector.change(fn=change_browser, inputs=browser_selector)
    temperature_slider.change(fn=change_temperature, inputs=temperature_slider)

app.queue().launch(debug=True, share=False)
