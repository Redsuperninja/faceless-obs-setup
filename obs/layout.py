#!/usr/bin/env python3
"""
Where things go. Everything on screen is placed from a handful of numbers in config.json under
"layout", so resizing is one edit and a rebuild (python setup_obs.py --reset).

    python layout.py show                         # the current numbers and the boxes they make
    python layout.py set sidebar_width 0.30       # wider right-hand column (horizontal layout)
    python layout.py set sidebar_height 0.45 --vertical
    python layout.py reset                        # back to the defaults

Numbers are fractions of the canvas (0.25 = a quarter). Horizontal layout (Twitch/YouTube):
  sidebar_width  width of the right-hand column that holds the art panel, goal bar and chat
  margin         space around everything (a fraction of the width; top and bottom match in pixels)
  deco_height    height of the art panel as a fraction of the canvas height; "auto" keeps it 16:9
  goal_height    height of the goal bar
  gap            space between the panels
Vertical layout (Twitch/TikTok/Shorts): no chat. The game fills the screen from game_top to game_bottom; the name
plate and goal bar overlay its top edge at top_offset (0.125 = an eighth of the way down); goal_height is their height.
"""

import argparse
import json
import sys
from pathlib import Path

CONFIG = Path(__file__).resolve().parent.parent / "config.json"
DEFAULTS = {
    "horizontal": {"sidebar_width": 0.24, "margin": 0.02, "deco_height": "auto", "goal_height": 0.075, "gap": 0.012},
    "vertical": {"top_offset": 0.125, "game_top": 0.10, "game_bottom": 0.90, "margin": 0.02, "deco_height": 0, "goal_height": 0.05, "gap": 0.01},
}


def settings(cfg, vertical):
    """The numbers in use: defaults overridden by config.json's "layout"."""
    which = "vertical" if vertical else "horizontal"
    return {**DEFAULTS[which], **cfg.get("layout", {}).get(which, {})}


def boxes(cfg, W, H, vertical, deco=True):
    """Every panel as an (x, y, w, h) box in canvas fractions: main, sidebar, deco, goal, chat (vertical also: plate).
    deco=False leaves the art panel out, so the chat grows to fill its space."""
    s = settings(cfg, vertical)
    mx = s["margin"]
    my = mx * W / H  # same pixel margin top and bottom as at the sides
    gap_y = s["gap"]
    if vertical:
        # No chat (Twitch draws its own over the stream). The game fills the screen between game_top and
        # game_bottom; the name plate and goal bar sit on its top edge, starting top_offset (about an eighth)
        # of the way down so Twitch's own overlays don't cover them.
        rh, top = s["goal_height"], s["top_offset"]
        main = (mx, s["game_top"], 1 - 2 * mx, s["game_bottom"] - s["game_top"])
        pw = (1 - 2 * mx) * 0.42
        plate = (mx, top, pw, rh)
        goal = (mx + pw + gap_y * 1.5, top, (1 - 2 * mx) - pw - gap_y * 1.5, rh)
        return {"main": main, "sidebar": None, "deco": None, "goal": goal, "chat": None, "plate": plate}
    else:
        sw = s["sidebar_width"]
        sidebar = (1 - mx - sw, my, sw, 1 - 2 * my)
        main = (mx, my, sidebar[0] - 2 * mx, 1 - 2 * my)
    x, y, w, h = sidebar
    dh = s["deco_height"]
    if dh == "auto":
        dh = w * W * 9 / 16 / H if not vertical else 0  # keep the art panel 16:9
    dh = min(float(dh), h * 0.6) if deco else 0
    deco = (x, y, w, dh) if dh > 0 else None
    y += dh + (gap_y if dh > 0 else 0)
    gh = s["goal_height"]
    goal = (x, y, w, gh) if gh > 0 else None
    y += gh + (gap_y if gh > 0 else 0)
    chat = (x, y, w, sidebar[1] + h - y)
    return {"main": main, "sidebar": sidebar, "deco": deco, "goal": goal, "chat": chat}


def _load():
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def _save(cfg):
    CONFIG.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", choices=["show", "set", "reset"])
    ap.add_argument("name", nargs="?")
    ap.add_argument("value", nargs="?")
    ap.add_argument("--vertical", action="store_true", help="change the vertical (TikTok/Shorts) layout")
    args = ap.parse_args()
    cfg = _load()
    which = "vertical" if args.vertical else "horizontal"
    if args.action == "set":
        if args.name not in DEFAULTS[which] or args.value is None:
            sys.exit(f"Usage: layout.py set <{'|'.join(DEFAULTS[which])}> <number>")
        try:
            value = args.value if args.value == "auto" else float(args.value)
        except ValueError:
            sys.exit("The value must be a number (or 'auto' for deco_height).")
        cfg.setdefault("layout", {}).setdefault(which, {})[args.name] = value
        _save(cfg)
        print(f"Set {which} {args.name} = {value}. Rebuild with:  python setup_obs.py --reset")
    elif args.action == "reset":
        cfg.get("layout", {}).pop(which, None)
        _save(cfg)
        print(f"{which} layout back to defaults. Rebuild with:  python setup_obs.py --reset")
    size = cfg.get("layouts", {}).get(which, {})
    W, H = size.get("width", 1080 if args.vertical else 1920), size.get("height", 1920 if args.vertical else 1080)
    print(f"\n{which} layout ({W}x{H}) numbers: {settings(cfg, args.vertical)}")
    for name, box in boxes(cfg, W, H, args.vertical).items():
        if box:
            x, y, w, h = box
            print(f"  {name:8} x={x:.3f} y={y:.3f} w={w:.3f} h={h:.3f}  ({int(w * W)}x{int(h * H)} px)")


if __name__ == "__main__":
    main()
