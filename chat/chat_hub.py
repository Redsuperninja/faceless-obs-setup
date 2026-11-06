#!/usr/bin/env python3
"""
One chat box for Twitch and YouTube, like Restream's.

    python chat_hub.py --youtube https://www.youtube.com/watch?v=XXXXXXXXXXX
    python chat_hub.py --demo        # fake messages, to line the box up in OBS

Then point OBS at http://localhost:8765/ (the setup script already does this for
the "Chat (browser)" source). Twitch needs only the channel name from config.json.
YouTube needs the env var YOUTUBE_API_KEY and the live video's link or id.
"""

import argparse
import itertools
import json
import os
import threading
import time
from pathlib import Path

from chat import alerts
from chat import chat_twitch
from chat import chat_youtube
from chat import eventsub
from chat import goal
from obs import layout
from chat.chat_server import ChatBus, make_server
from chat.commands import Commands

from accounts.env_loader import load_env

HERE = Path(__file__).resolve().parent.parent
load_env()
DEMO = [("twitch", "Viewer1", "#FF4500", "hello from Twitch!"),
        ("youtube", "Viewer2", "", "hello from YouTube!"),
        ("twitch", "Mod_Person", "#1E90FF", "!guild"),
        ("youtube", "Fan3", "", "love the overlay")]
DEMO_ALERTS = [{"type": "alert", "kind": "follow", "user": "NewFriend", "detail": "", "platform": "twitch"},
               {"type": "alert", "kind": "raid", "user": "Wanderer", "detail": "12", "platform": "twitch"},
               {"type": "alert", "kind": "sub", "user": "Viewer1", "detail": "", "platform": "twitch"},
               {"type": "alert", "kind": "superchat", "user": "Fan3", "detail": "$5.00",
                "comment": "for the music!", "platform": "youtube"}]


def make_publish(bus, cfg):
    """One door for everything the readers produce: alerts get styled, chat commands become cards."""
    cmds = Commands(cfg.get("commands", {}))

    min_bits = cfg.get("alerts", {}).get("min_bits", 50)

    def publish(msg):
        if msg.get("kind") == "bits" and int(msg.get("detail") or 0) < min_bits:
            return  # a 1-bit cheer should not hold the screen for 8 seconds
        bus.publish(alerts.decorate(msg, cfg) if msg.get("type") else msg)
        event = cmds.handle(msg)
        if event:
            bus.publish(alerts.decorate(event, cfg))
    return publish


def start_readers(bus, twitch_name, youtube_video, youtube_key, stop, demo=False, publish=None):
    """Start one background thread per chat source. Returns the threads."""
    jobs = []
    publish = publish or bus.publish
    if demo:
        def fake():
            for i, (p, u, c, t) in enumerate(itertools.cycle(DEMO)):
                if stop.wait(2):
                    return
                publish({"platform": p, "user": u, "color": c, "text": t, "id": f"demo{i}", "mod": u == "Mod_Person"})
                if i % 6 == 5:  # an alert every so often, so you can see how they look
                    publish(dict(DEMO_ALERTS[(i // 6) % len(DEMO_ALERTS)]))
        jobs.append(fake)
    if twitch_name and not demo:
        jobs.append(lambda: chat_twitch.run(twitch_name, publish, stop))
    if twitch_name and not demo and os.environ.get("TWITCH_CLIENT_ID"):
        jobs.append(lambda: eventsub.run(publish, stop))  # follow alerts (needs the follower sign-in)
    if not twitch_name and not demo:
        print("Twitch chat: skipped (set channel.twitch_name in config.json)")
    if youtube_video and youtube_key and not demo:
        vid = chat_youtube.video_id_from(youtube_video)
        if vid:
            jobs.append(lambda: chat_youtube.run(youtube_key, vid, publish, stop))
        else:
            print("YouTube chat: skipped (could not read a video id from that link)")
    elif youtube_video and not youtube_key and not demo:
        print("YouTube chat: skipped (set the YOUTUBE_API_KEY environment variable)")
    threads = [threading.Thread(target=j, daemon=True) for j in jobs]
    for t in threads:
        t.start()
    return threads


def serve(cfg, youtube_video="", demo=False):
    """Run the chat box until Ctrl+C."""
    port = cfg.get("chat", {}).get("port", 8765)
    bus, stop = ChatBus(), threading.Event()
    start_readers(bus, cfg["channel"].get("twitch_name", ""), youtube_video,
                  os.environ.get("YOUTUBE_API_KEY", ""), stop, demo, make_publish(bus, cfg))
    threading.Thread(target=goal.keep_fresh, args=(stop,), daemon=True).start()
    size = cfg.get("layouts", {}).get("horizontal", {})
    mx, _, mw, _ = layout.boxes(cfg, size.get("width", 1920), size.get("height", 1080), False)["main"]
    srv = make_server(bus, port, {"/style.json": lambda: {**cfg["style"], "fonts": cfg.get("fonts", {}),
                                                          "alert_x": mx + mw / 2},  # cards centre over the main area
                                  "/goal.json": goal.read})
    print(f"Combined chat running at http://localhost:{port}/  (alerts: /overlay, goal: /goal; Ctrl+C to stop)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        srv.server_close()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=str(HERE / "config.json"))
    ap.add_argument("--youtube", default="", help="YouTube live link or video id")
    ap.add_argument("--demo", action="store_true", help="show fake messages instead of real chat")
    args = ap.parse_args()
    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    serve(cfg, args.youtube, args.demo)


if __name__ == "__main__":
    main()
