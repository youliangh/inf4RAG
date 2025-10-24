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
    message = message.replace("{{TOOLS_PROMPT}}", llm_tools.get_tool_list_for_prompt())

    return message

def generate(new_user_message, history):
    """
    Generate a response from the LLM to the user message while using the 
    available tools.  The history contains a list of prior 
    (user_message, assistant_response) pairs from the chat.
    This function is intended to be called by a Gradio ChatInterface.

    Within this function, we iteratively build up a prompt which includes
    the complete reasoning chain of:

       Question -> [Thought -> Action -> Result?] x N -> Conclusion

    Ideally, we would include the Result for every Action.  For most models,
    we quickly use up the entire context window when including the contents
    of web pages, so we only include the Result for the most recent Action.

    Note that Claude 2 supports a 100k context window, but in practice, I've
    found that the Anthropic API will return a rate limit error if I actually 
    try to send a large number of tokens, so unfortuantely I use the same logic
    with Claude 2 as the other models.
    """
    ACTION_REGEX = r'(\n|^)Action: (.*)\[(.*)\]'
    CONCLUSION_REGEX = r'(\n|^)Conclusion: .*'

    prompt = f"Question: {new_user_message}\n\n"

    # full_response is displayed to the user in the ChatInterface and is the
    # same as the prompt, except it omits the Question and Result to improve
    # readability.
    full_response = ""

    iteration = 1

    model = MODELS["vLLM"]

    try:
        while True:
            if verbose:
                print("======")
                print("PROMPT")
                print("======")
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
                    # Stream each completion to the ChatInterface
                    full_response += completion
                    partial_response += completion
                    yield full_response

                    # When we find an Action in the response, stop the
                    # generation, run the tool specified in the Action,
                    # and create a new prompt that includes the Results.
                    matches = re.search(ACTION_REGEX, partial_response)
                    if matches:
                        tool = matches.group(2).strip()
                        params = matches.group(3).strip()
                        
                        result = llm_tools.run_tool(tool, params)

                        prompt = f"Question: {new_user_message}\n\n"
                        prompt += f"{full_response}\n\n"

                        prompt += f"Result: {result}\n\n"

                        break

            # Stop when we either see the Conclusion or we cannot find an 
            # Action in the response
            if re.search(CONCLUSION_REGEX, partial_response) or not re.search(ACTION_REGEX, partial_response):
                return
                        
            if not partial_response.endswith("\n"):
                full_response += "\n\n"
                yield full_response
            
            # Stop when we've exceeded max_actions
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
    print("==============")
    print("SYSTEM MESSAGE")
    print("==============")
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
