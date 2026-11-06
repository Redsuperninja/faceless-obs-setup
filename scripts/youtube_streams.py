"""Make (or find) two reusable YouTube live streams, one for the 16:9 picture and one for the 9:16 picture,
and save their keys in the git-ignored .env as YOUTUBE_STREAM_KEY_H and YOUTUBE_STREAM_KEY_V.

    python youtube_streams.py

Safe to rerun: streams are found by title first. Keys are never printed. A reusable stream is only a
key; it does not go live or show anything until OBS sends video and a broadcast is started.
"""

import _root  # noqa: F401  (puts the project folder on the path)

import sys
import urllib.parse
from pathlib import Path

from accounts import tokens
from accounts.env_loader import DEFAULT as ENV_PATH
from accounts.stream_push import _request

API = "https://www.googleapis.com/youtube/v3/liveStreams"
WANTED = {"YOUTUBE_STREAM_KEY_H": "OBS horizontal (16:9)", "YOUTUBE_STREAM_KEY_V": "OBS vertical (9:16)"}
ADDRESS_VAR = "YOUTUBE_RTMP_URL"


def find_or_create(headers, title):
    listing = _request("GET", f"{API}?part=snippet,cdn&mine=true&maxResults=50", headers)
    for s in listing.get("items", []):
        if s["snippet"]["title"] == title:
            return s
    body = {"snippet": {"title": title},
            "cdn": {"frameRate": "variable", "ingestionType": "rtmp", "resolution": "variable"},
            "contentDetails": {"isReusable": True}}
    return _request("POST", f"{API}?part=snippet,cdn,contentDetails", headers, body)


def save_env(values):
    """Add or replace KEY=value lines in .env without touching anything else."""
    path = Path(ENV_PATH)
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    kept = [ln for ln in lines if ln.split("=", 1)[0].strip() not in values]
    path.write_text("\n".join(kept + [f"{k}={v}" for k, v in values.items()]) + "\n", encoding="utf-8")


def main():
    token = tokens.access_token("youtube")
    if not token:
        sys.exit("Not signed in to YouTube: run get_tokens.py first.")
    headers = {"Authorization": f"Bearer {token}"}
    values = {}
    for var, title in WANTED.items():
        info = find_or_create(headers, title)["cdn"]["ingestionInfo"]
        values[var] = info["streamName"]
        values[ADDRESS_VAR] = info["ingestionAddress"]
        print(f"ok: {title}")
    save_env(values)
    print(f"Saved to .env: {', '.join(values)} (values not shown).")


if __name__ == "__main__":
    main()
