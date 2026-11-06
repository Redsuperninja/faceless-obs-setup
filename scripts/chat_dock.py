"""Add the combined Twitch + YouTube chat as a dock inside OBS (View > Docks > "Chat (Twitch + YouTube)").

    python chat_dock.py            # close OBS first: OBS rewrites its settings when it exits
    python chat_dock.py --ini PATH # use another settings file (for testing)

The dock shows the page chat_hub.py serves, so run start_stream.py (or chat_hub.py) to fill it. Safe to rerun.
"""

import argparse
import codecs
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

TITLE = "Chat (Twitch + YouTube)"


def obs_running():
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq obs64.exe"], capture_output=True, text=True).stdout
    return "obs64.exe" in out


def add_dock(text, url, title=TITLE):
    """Return the ini text with the dock added (or its address updated)."""
    lines = text.splitlines()
    for i, ln in enumerate(lines):
        if ln.startswith("ExtraBrowserDocks="):
            docks = json.loads(ln.split("=", 1)[1] or "[]")
            found = next((d for d in docks if d.get("title") == title), None)
            if found:
                found["url"] = url
            else:
                docks.append({"title": title, "url": url, "uuid": str(uuid.uuid4())})
            lines[i] = "ExtraBrowserDocks=" + json.dumps(docks, separators=(",", ":"))
            return "\n".join(lines) + "\n"
    raise SystemExit("This settings file has no ExtraBrowserDocks line (start OBS once, then close it).")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ini", help="settings file (default: OBS's user.ini)")
    args = ap.parse_args()
    cfg = json.loads((Path(__file__).resolve().parent.parent / "config.json").read_text(encoding="utf-8"))
    url = f"http://localhost:{cfg.get('chat', {}).get('port', 8765)}/?bg=1&size=20"
    if args.ini:
        paths = [Path(args.ini)]
    else:
        if obs_running():
            sys.exit("Close OBS first (it overwrites its settings when it exits), then run this again.")
        base = Path(os.environ["APPDATA"]) / "obs-studio"
        paths = [base / "user.ini", base / "global.ini"]
    for p in paths:
        if p.exists():
            had_bom = p.read_bytes().startswith(codecs.BOM_UTF8)  # OBS writes its ini files with a BOM
            p.write_text(add_dock(p.read_text(encoding="utf-8-sig"), url), encoding="utf-8-sig" if had_bom else "utf-8")
            print(f"Added the chat dock to {p.name}.")
    print("Open OBS > View > Docks > 'Chat (Twitch + YouTube)'. It fills once chat_hub.py is running.")


if __name__ == "__main__":
    main()
