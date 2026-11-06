"""Keeps sign-in tokens fresh. Refresh tokens live in tokens.json, outside the project folder
(the "twitch-tools" folder under LOCALAPPDATA, or the path in TOKENS_FILE) so OneDrive and git never see it.

access_token(service) returns a working access token:
  1. a saved one that has not expired, else
  2. a new one made from the saved refresh token (needs the client ID and secret in .env), else
  3. the plain TWITCH_ACCESS_TOKEN / YOUTUBE_ACCESS_TOKEN variable, else "".
"""

import json
import os
import time
from pathlib import Path

from accounts.oauth_flow import post_form



def _default_path():
    """Outside the project, so OneDrive and git never see it. Override with TOKENS_FILE."""
    if os.environ.get("TOKENS_FILE"):
        return Path(os.environ["TOKENS_FILE"])
    base = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), ".config")
    return Path(base) / "twitch-tools" / "tokens.json"


PATH = _default_path()
SERVICES = {
    "twitch": {"token_url": "https://id.twitch.tv/oauth2/token", "id": "TWITCH_CLIENT_ID",
               "secret": "TWITCH_CLIENT_SECRET", "fallback": "TWITCH_ACCESS_TOKEN"},
    "youtube": {"token_url": "https://oauth2.googleapis.com/token", "id": "YOUTUBE_CLIENT_ID",
                "secret": "YOUTUBE_CLIENT_SECRET", "fallback": "YOUTUBE_ACCESS_TOKEN"},
}


def _load():
    try:
        return json.loads(PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_tokens(service, reply):
    """Store a token reply from Twitch or Google (keeps the old refresh token if none is sent)."""
    data = _load()
    old = data.get(service, {})
    data[service] = {
        "refresh_token": reply.get("refresh_token") or old.get("refresh_token", ""),
        "access_token": reply["access_token"],
        "expires_at": time.time() + int(reply.get("expires_in", 3600)),
    }
    PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = PATH.with_name(PATH.name + ".tmp")  # write then swap, so a crash can't leave half a file
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)  # owner-only where supported
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(json.dumps(data, indent=2) + "\n")
    os.replace(tmp, PATH)


def access_token(service):
    cfg = SERVICES[service]
    entry = _load().get(service, {})
    if entry.get("access_token") and entry.get("expires_at", 0) > time.time() + 60:
        return entry["access_token"]
    client_id, secret = os.environ.get(cfg["id"]), os.environ.get(cfg["secret"])
    if entry.get("refresh_token") and client_id and secret:
        reply = post_form(cfg["token_url"], {
            "client_id": client_id, "client_secret": secret,
            "grant_type": "refresh_token", "refresh_token": entry["refresh_token"]})
        save_tokens(service, reply)
        return reply["access_token"]
    return os.environ.get(cfg["fallback"], "")
