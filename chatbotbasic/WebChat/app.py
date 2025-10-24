import re
import datetime
import gradio as gr
import yaml

from models import OpenAIModel
from tools import Tools

SYSTEM_MESSAGE_TEMPLATE = "prompt.txt"

with open("config.yaml", "r") as config_file:
    config = yaml.safe_load(config_file)

# synthesize the base_url
config["base_url"] = f"http://{config.get('openstack_ip_port', '127.0.0.1:8000')}/v1"

MODELS = {
    "vLLM": OpenAIModel(config)
}

verbose = config["verbose"]
description = config["description"]
examples = config["examples"]
temperature = config["temperature"]
max_actions = config["max_actions"]

llm_tools = Tools()

def create_system_message():
    """
    Return system message, including today's date and the available tools.
    """
    with open(SYSTEM_MESSAGE_TEMPLATE) as f:
        message = f.read()

    now = datetime.datetime.now()
    current_date = now.strftime("%B %d, %Y")

    message = message.replace("{{CURRENT_DATE}}", current_date)

    return message

def generate(new_user_message, history):
    prompt = new_user_message

    # full_response is displayed to the user in the ChatInterface and is the
    # same as the prompt, except it omits the Question and Result to improve
    # readability.
    full_response = ""

    iters = 0
    model = MODELS["vLLM"]

    try:
        while True:
            if verbose:
                print("="*80)
                print(f"ITERATION {iters}")
                print("="*80)
                print(prompt)

            stream = model.generate(
                system_message,
                prompt,
                history=history,
                temperature=temperature
            )

            for chunk in stream:
                completion = model.parse_completion(chunk)

                if completion:
                    # Stream each completion to the ChatInterface
                    full_response += completion
                    yield full_response
            
            return
    
    except Exception as e:
        full_response += f"\n<span style='color:red'>Error: {e}</span>"
        yield full_response


# Create Gradio app
system_message = create_system_message()
if verbose:
    print("="*80)
    print("SYSTEM PROMPT:")
    print("="*80)
    print(system_message)

CSS = """
h1 { text-align: center; }
h3 { text-align: center; }
.contain { display: flex; flex-direction: column; }
.gradio-container { height: 100vh !important; }
#component-0 { flex-grow: 1; overflow: auto; }
#chatbot { flex-grow: 1; overflow: auto; }
"""

with gr.Blocks(css=CSS) as app:
    gr.Markdown(description)
    chatinterface = gr.ChatInterface(fn=generate, examples=examples)
    chatinterface.chatbot.elem_id = "chatbot"

    with gr.Accordion(label="Options", open=False):
        with gr.Row():
            model_name_box = gr.Textbox(
                label="Model Name",
                placeholder="N/A",
                value=MODELS["vLLM"].model_name
            )

            base_url_box = gr.Textbox(
                label="Request URL",
                placeholder="https://api.openai.com/v1",
                value=f"{config.get('base_url', 'https://api.openai.com/v1')}/api_key={config.get('api_key', '')}"
            )

            temperature_slider = gr.Slider(label="Temperature", minimum=0, maximum=1, step=0.1, value=temperature)
        

    def change_temperature(new_temperature):
        global temperature
        temperature = new_temperature

    temperature_slider.change(fn=change_temperature, inputs=temperature_slider)

app.queue().launch(debug=True, share=False)
