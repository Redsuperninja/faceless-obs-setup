#!/usr/bin/env python3
"""
The goal bar's numbers live in goal.json. Change them with:

    python goal.py 42                          # set the current count
    python goal.py --target 100 --label "Road to 100 followers"
    python goal.py --source twitch_followers   # let the chat box keep the count up to date
    python goal.py --source manual             # back to typing it yourself

twitch_followers needs the "moderator:read:followers" permission: run `python get_tokens.py twitch`
once after updating, and keep chat_hub.py running (it refreshes the count every minute).
"""

import argparse
import json
from pathlib import Path

PATH = Path(__file__).resolve().parent.parent / "data" / "goal.json"
DEFAULT = {"label": "Next goal", "current": 0, "target": 100, "source": "manual"}


def read(path=PATH):
    """The goal as a dict (defaults filled in; a missing or broken file gives the defaults)."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    return {**DEFAULT, **{k: v for k, v in data.items() if k in DEFAULT}}


def write(goal, path=PATH):
    Path(path).write_text(json.dumps(goal, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def twitch_follower_count():
    """Total followers, from Twitch (needs the moderator:read:followers sign-in)."""
    import os

    from accounts import stream_push
    from accounts import tokens
    headers = {"Client-Id": os.environ.get("TWITCH_CLIENT_ID", ""),
               "Authorization": f"Bearer {tokens.access_token('twitch')}"}
    me = stream_push._request("GET", "https://api.twitch.tv/helix/users", headers)["data"][0]["id"]
    return int(stream_push._request(
        "GET", f"https://api.twitch.tv/helix/channels/followers?broadcaster_id={me}&first=1", headers)["total"])


def keep_fresh(stop, log=print, every=60, path=PATH):
    """Background loop for chat_hub: refresh `current` while source is twitch_followers."""
    warned = False
    while not stop.wait(every):
        goal = read(path)
        if goal["source"] != "twitch_followers":
            continue
        try:
            goal["current"] = twitch_follower_count()
            write(goal, path)
            warned = False
        except (RuntimeError, OSError, KeyError, ValueError) as e:
            if not warned:  # say it once, not every minute
                log(f"Goal: could not read followers ({e}); run  python get_tokens.py twitch  to allow it")
                warned = True


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("current", nargs="?", type=int, help="the current count")
    ap.add_argument("--target", type=int)
    ap.add_argument("--label")
    ap.add_argument("--source", choices=["manual", "twitch_followers"])
    args = ap.parse_args()
    goal = read()
    for key in ("current", "target", "label", "source"):
        if getattr(args, key) is not None:
            goal[key] = getattr(args, key)
    write(goal)
    print(f"Goal: {goal['label']}: {goal['current']} / {goal['target']} ({goal['source']})")


if __name__ == "__main__":
    main()
