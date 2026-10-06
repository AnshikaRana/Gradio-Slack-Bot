"""Optional: your own Gradio app for the Slack bot to talk to.
A multimodal chat app answered by a local Ollama model (free, no API key).
Run it, then set GRADIO_APP=http://127.0.0.1:7860/ in .env."""
import json
import os

import gradio as gr
import httpx
from dotenv import load_dotenv

load_dotenv()
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
SYSTEM = """You are Gradio Playground Bot. When the user describes an app, reply with one short
sentence, then complete, runnable Python code in a ```python block that builds the app with
gradio's gr.Interface (or gr.Blocks), following EXACTLY this correct pattern:

```python
import gradio as gr

def reverse_text(text):
    return text[::-1]

demo = gr.Interface(
    fn=reverse_text,
    inputs=gr.Textbox(label="Text"),
    outputs=gr.Textbox(label="Reversed"),
    title="Text Reverser",
)

demo.launch()
```

Valid components include gr.Textbox, gr.Number, gr.Dropdown(choices=[...]), gr.Slider,
gr.Checkbox, gr.Image, gr.Audio. Use a list for several inputs, e.g. inputs=[gr.Number(), gr.Number()].
For any other question, answer briefly in plain markdown."""


def chat(message, history):
    """message = {"text": str, "files": [paths]}; streams the answer."""
    text = message.get("text", "") if isinstance(message, dict) else str(message)
    files = message.get("files", []) if isinstance(message, dict) else []
    if files:
        text += f"\n\n(The user attached {len(files)} image(s); this text-only model cannot see them.)"

    messages = [{"role": "system", "content": SYSTEM}]
    for turn in history:
        if isinstance(turn, dict) and isinstance(turn.get("content"), str):
            messages.append({"role": turn["role"], "content": turn["content"]})
    messages.append({"role": "user", "content": text})

    answer = ""
    with httpx.stream(
        "POST", OLLAMA_URL, json={"model": MODEL, "messages": messages, "stream": True}, timeout=300
    ) as r:
        for line in r.iter_lines():
            if line:
                answer += json.loads(line).get("message", {}).get("content", "")
                yield answer


demo = gr.ChatInterface(
    fn=chat,
    multimodal=True,
    title="Gradio Playground Bot (local)",
    description=f"Describe an app and get Gradio code. Runs on {MODEL} via Ollama; also served to Slack through bot.py.",
    examples=[{"text": "create a simple calculator app"}, {"text": "an app that reverses text"}],
)

if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860)
