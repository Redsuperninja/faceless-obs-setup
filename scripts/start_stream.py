#!/usr/bin/env python3
"""
Run this when you start a stream. It asks for the title, description and category
(press Enter to keep your last answer), saves them, sets them on Twitch and YouTube,
then starts the combined chat box.

    python start_stream.py              # ask, save, push, start chat
    python start_stream.py --yes        # reuse the saved answers without asking
    python start_stream.py --dry-run    # show what would be sent; change nothing online
    python start_stream.py --no-chat    # skip the chat box
    python start_stream.py --no-vertical  # 16:9 only: skip the vertical scene sync

Order of a stream night: create the YouTube stream in YouTube Studio (Go live) so it
has a link, open OBS (obs-multi-rtmp set up), run this, then press Start Streaming.
"""

import _root  # noqa: F401  (puts the project folder on the path)

import argparse
import json
from pathlib import Path

from chat import chat_hub
from obs import scene_sync
from accounts import stream_push

from accounts.env_loader import load_env

HERE = Path(__file__).resolve().parent.parent
load_env()
SAVED = HERE / "data" / "stream_info.json"          # your last answers (git-ignored)
EXAMPLE = HERE / "data" / "stream_info.example.json"
QUESTIONS = [
    ("title", "Title (YouTube cuts it at 100 characters)"),
    ("description", "Description (YouTube only; type \\n for a new line)"),
    ("category", "Twitch category / game"),
    ("tags", "Tags, comma separated (Twitch keeps 10; letters and numbers only)"),
    ("youtube_category_id", "YouTube category id (20 = Gaming, 22 = People & Blogs)"),
    ("youtube_video", "YouTube live link or video id (blank = skip YouTube)"),
]


def load_info():
    src = SAVED if SAVED.exists() else EXAMPLE
    return json.loads(src.read_text(encoding="utf-8"))


def ask(info, input_fn=input):
    """Show each saved answer in [brackets]; Enter keeps it."""
    out = dict(info)
    for key, label in QUESTIONS:
        shown = str(out.get(key, "")).replace("\n", "\\n")
        answer = input_fn(f"{label}\n  [{shown}] > ").strip()
        if answer:
            out[key] = answer.replace("\\n", "\n")
    return out


def push_all(info, dry_run):
    video = chat_hub.chat_youtube.video_id_from(info.get("youtube_video", ""))
    if dry_run:
        print(f"[dry-run] Twitch: title={info['title'][:stream_push.TWITCH_MAX_TITLE]!r} "
              f"category={info.get('category')!r}")
        print(f"[dry-run] YouTube video {video or '(none)'}: title={info['title'][:stream_push.YOUTUBE_MAX_TITLE]!r} "
              f"category id={info.get('youtube_category_id')!r}")
        return
    for name, fn in (("Twitch", lambda: stream_push.push_twitch(info)),
                     ("YouTube", lambda: stream_push.push_youtube(info, video))):
        try:
            print(f"{name}: {fn()}")
        except (RuntimeError, OSError) as e:
            print(f"{name}: failed: {e}")
    print("If a line says skipped or failed, set that one by hand in Twitch Stream Manager / YouTube Studio.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--yes", action="store_true", help="reuse saved answers, don't ask")
    ap.add_argument("--dry-run", action="store_true", help="show what would be sent, change nothing online")
    ap.add_argument("--no-chat", action="store_true", help="don't start the combined chat box")
    ap.add_argument("--no-vertical", action="store_true", help="don't start the vertical-canvas scene sync")
    args = ap.parse_args()

    info = load_info()
    if not args.yes:
        info = ask(info)
    if not info.get("title"):
        raise SystemExit("A title is required.")
    SAVED.write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")

    push_all(info, args.dry_run)
    cfg = json.loads((HERE / "config.json").read_text(encoding="utf-8"))
    if not args.dry_run and not args.no_vertical:
        scene_sync.start(cfg)  # vertical scenes follow the main canvas by name
    if not args.no_chat:
        chat_hub.serve(cfg, info.get("youtube_video", ""))


if __name__ == "__main__":
    main()
