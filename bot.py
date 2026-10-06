"""Slack bot that forwards @mentions (text + images) to a Gradio app and
replies with the app's answer. Based on the Gradio guide
"Creating a Slack Bot from a Gradio App", with the missing imports added,
tokens read from .env, streamed answers shown in a single updating message,
and basic error handling."""
import os
import re
import time

import httpx
from dotenv import load_dotenv
from gradio_client import Client, handle_file
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

load_dotenv()
SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]  # xoxb-...
SLACK_APP_TOKEN = os.environ["SLACK_APP_TOKEN"]  # xapp-...
GRADIO_APP = os.getenv("GRADIO_APP", "abidlabs/gradio-playground-bot")
UPDATE_EVERY = 1.5  # seconds between Slack message edits while streaming

app = App(token=SLACK_BOT_TOKEN)
print(f"Connecting to Gradio app: {GRADIO_APP}")
gradio_client = Client(GRADIO_APP)


def download_image(url, filename):
    """Slack file URLs are private, so the bot token is needed to download them."""
    headers = {"Authorization": f"Bearer {SLACK_BOT_TOKEN}"}
    response = httpx.get(url, headers=headers, follow_redirects=True, timeout=60)
    response.raise_for_status()
    os.makedirs("./images", exist_ok=True)
    image_path = os.path.join("./images", os.path.basename(filename))
    with open(image_path, "wb") as f:
        f.write(response.content)
    return image_path


def slackify_message(message):
    """Convert markdown links to Slack's <url|text> format and drop the language
    name after ``` (Slack doesn't support it)."""
    pattern = r"\[(.*?)\]\((.*?)\)"
    cleaned = re.sub(pattern, r"<\2|\1>", message)
    cleaned = re.sub(r"```\w+\n", "```\n", cleaned)
    return cleaned.strip()


def extract_text(response):
    """Gradio apps can return a string, a list of chat messages or a dict.
    Pull out the latest text in all cases."""
    if response is None:
        return ""
    if isinstance(response, str):
        return response
    if isinstance(response, (list, tuple)):
        # e.g. [answer, None] or a list of chat messages: take the last non-empty item
        for item in reversed(response):
            text = extract_text(item)
            if text:
                return text
        return ""
    if isinstance(response, dict):
        content = response.get("content", response.get("text", ""))
        if isinstance(content, list):  # list of content blocks
            return "".join(
                c.get("text", "") if isinstance(c, dict) else str(c) for c in content
            )
        return str(content)
    return str(response)


@app.event("app_mention")
def handle_app_mention_events(body, say, client):
    event = body["event"]
    channel = event["channel"]
    thread_ts = event.get("thread_ts", event["ts"])  # reply in a thread

    # Extract the message content without the bot mention
    bot_user_id = body["authorizations"][0]["user_id"]
    clean_message = event.get("text", "").replace(f"<@{bot_user_id}>", "").strip()

    # Handle an attached image if present
    files = []
    for file in event.get("files", []):
        if file.get("filetype") in ["png", "jpg", "jpeg", "gif", "webp"]:
            image_path = download_image(file["url_private_download"], file["name"])
            files.append(handle_file(image_path))
            break

    print(f"Mention received: {clean_message!r} (+{len(files)} image)")
    placeholder = say(text=":hourglass_flowing_sand: Thinking...", thread_ts=thread_ts)
    msg_ts = placeholder["ts"]

    try:
        latest, last_update = "", 0.0
        # Submit to Gradio and stream the answer into one Slack message
        job = gradio_client.submit(
            message={"text": clean_message, "files": files}, api_name="/chat"
        )
        for response in job:
            latest = slackify_message(extract_text(response))
            if latest and time.time() - last_update > UPDATE_EVERY:
                client.chat_update(channel=channel, ts=msg_ts, text=latest[:3900])
                last_update = time.time()
        # If the Gradio app failed part-way, job.result() raises its error
        try:
            latest = slackify_message(extract_text(job.result())) or latest
        except Exception as e:
            raise RuntimeError(f"The Gradio app returned an error: {e or 'unknown error'}")
        final = latest or "(The Gradio app returned an empty response.)"
        client.chat_update(channel=channel, ts=msg_ts, text=final[:3900])
        print("Reply sent.")
    except Exception as e:  # show errors in Slack instead of failing silently
        client.chat_update(
            channel=channel, ts=msg_ts, text=f":warning: {e}"
        )
        print(f"Error: {e}")


@app.event("message")
def ignore_plain_messages(body, logger):
    """Plain channel messages are not for the bot; only @mentions are."""
    pass


@app.event("app_home_opened")
def ignore_app_home(body, logger):
    pass


if __name__ == "__main__":
    print("Slack bot running - mention it in a channel it was invited to. Ctrl+C to stop.")
    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.start()
