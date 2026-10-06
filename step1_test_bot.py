"""Step 1 of the Gradio guide: a minimal Slack bot that only echoes mentions.
Run this first to confirm the Slack app, tokens and Socket Mode are working."""
import os

from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

load_dotenv()
SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_APP_TOKEN = os.environ["SLACK_APP_TOKEN"]

app = App(token=SLACK_BOT_TOKEN)


@app.event("app_mention")
def handle_app_mention_events(body, say):
    user_id = body["event"]["user"]
    say(f"Hi <@{user_id}>! You mentioned me and said: {body['event']['text']}")


if __name__ == "__main__":
    print("Echo bot running - mention it in Slack. Press Ctrl+C to stop.")
    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.start()
