"""Twitch follow alerts, over Twitch's EventSub WebSocket.

Twitch tells only a signed-in app about new followers, so this needs the one-time sign-in with the
"moderator:read:followers" permission (python get_tokens.py twitch) and TWITCH_CLIENT_ID in .env.
Everything else (subs, raids, cheers) comes through chat and needs no sign-in.
"""

import json
import os

import websocket  # comes with obsws-python

from accounts import stream_push
from accounts import tokens

URL = "wss://eventsub.wss.twitch.tv/ws"
SUBSCRIPTIONS = "https://api.twitch.tv/helix/eventsub/subscriptions"


def parse_follow(message):
    """A follow alert event from an EventSub message, or None for anything else."""
    meta = message.get("metadata", {})
    if meta.get("message_type") != "notification" or meta.get("subscription_type") != "channel.follow":
        return None
    event = message.get("payload", {}).get("event", {})
    return {"type": "alert", "kind": "follow", "platform": "twitch", "detail": "",
            "user": event.get("user_name") or event.get("user_login") or "Someone"}


def subscribe(session_id):
    """Ask Twitch to send follows for this connection (raises RuntimeError with Twitch's reason)."""
    headers = {"Client-Id": os.environ.get("TWITCH_CLIENT_ID", ""),
               "Authorization": f"Bearer {tokens.access_token('twitch')}"}
    me = stream_push._request("GET", "https://api.twitch.tv/helix/users", headers)["data"][0]["id"]
    stream_push._request("POST", SUBSCRIPTIONS, headers, {
        "type": "channel.follow", "version": "2",
        "condition": {"broadcaster_user_id": me, "moderator_user_id": me},
        "transport": {"method": "websocket", "session_id": session_id}})


def run(publish, stop, log=print, url=URL):
    """Stay connected and publish follow alerts until `stop` is set. Reconnects on its own."""
    warned, resume_url = False, None
    while not stop.is_set():
        try:
            ws = websocket.create_connection(resume_url or url, timeout=45)
            subscribed, resume_url = bool(resume_url), None  # a Twitch-requested move keeps its subscription
            try:
                while not stop.is_set():
                    message = json.loads(ws.recv())
                    kind = message.get("metadata", {}).get("message_type")
                    if kind == "session_welcome" and not subscribed:
                        subscribe(message["payload"]["session"]["id"])
                        subscribed = True
                        log("Twitch follows: listening")
                    elif kind == "session_reconnect":
                        resume_url = message["payload"]["session"]["reconnect_url"]
                        break
                    alert = parse_follow(message)
                    if alert:
                        publish(alert)
            finally:
                ws.close()
        except RuntimeError as e:  # Twitch refused (usually: missing permission)
            if not warned:
                log(f"Twitch follows: {e}\n  Run  python get_tokens.py twitch  to allow follow alerts.")
                warned = True
            stop.wait(600)
        except (OSError, websocket.WebSocketException, ValueError) as e:
            log(f"Twitch follows: connection lost ({e}); retrying in 10s")
            stop.wait(10)
