#!/usr/bin/env python3
"""
A small window to pick what opens, so you don't need the command line. Build the .exe with build_launcher.ps1.

Pick a layout (16:9 only, 9:16 only, or both) and an action:
  Start stream night   start_stream.py   (asks for title etc. in its own console)
  Build OBS scenes     setup_obs.py      (tick "Rebuild" to add --reset)
  Chat only            chat_hub.py
Your last choice is remembered in launcher_choice.json (git-ignored).
"""

import json
import subprocess
import sys
from pathlib import Path

LAYOUTS = {"horizontal": "16:9 only (Twitch / YouTube)", "vertical": "9:16 only (vertical)", "both": "Both"}
ACTIONS = {"stream": "Start stream night", "build": "Build OBS scenes", "chat": "Chat only"}


def project_dir():
    """The folder holding config.json: next to the exe/script, or one level up (exe in dist/)."""
    here = Path(sys.executable if getattr(sys, "frozen", False) else __file__).resolve().parent
    for d in (here, here.parent):
        if (d / "config.json").exists():
            return d
    return here


def python_for(root):
    """The project's own venv Python (it has obsws-python); else the Python running this script."""
    venv = root / ".venv" / "Scripts" / "python.exe"
    if venv.exists():
        return str(venv)
    return "python" if getattr(sys, "frozen", False) else sys.executable


def command(action, layout, rebuild=False, py="python"):
    """The command line for a choice. 'horizontal' keeps the vertical canvas out of everything."""
    if action == "build":
        cmd = [py, "scripts/setup_obs.py", "--layout", layout]
        return cmd + (["--reset"] if rebuild else [])
    if action == "chat":
        return [py, "scripts/chat_hub.py"]
    if action == "stream":
        return [py, "scripts/start_stream.py"] + (["--no-vertical"] if layout == "horizontal" else [])
    raise ValueError(f"unknown action {action!r}")


def run(action, layout, rebuild):
    root = project_dir()
    flags = subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0
    cmd = command(action, layout, rebuild, python_for(root))
    # Keep the console open afterwards so errors can be read.
    if sys.platform == "win32":
        cmd = ["cmd", "/k"] + cmd
    subprocess.Popen(cmd, cwd=root, creationflags=flags)


def main():
    import tkinter as tk
    root_dir = project_dir()
    saved_file = root_dir / "launcher_choice.json"
    try:
        saved = json.loads(saved_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        saved = {}
    win = tk.Tk()
    win.title("Stream launcher")
    layout = tk.StringVar(value=saved.get("layout", "horizontal"))
    rebuild = tk.BooleanVar(value=False)
    tk.Label(win, text="What should open?", font=("Segoe UI", 12, "bold")).pack(padx=16, pady=(12, 4), anchor="w")
    for key, label in LAYOUTS.items():
        tk.Radiobutton(win, text=label, variable=layout, value=key).pack(padx=24, anchor="w")
    tk.Checkbutton(win, text="Rebuild scenes from scratch (--reset)", variable=rebuild).pack(padx=16, pady=6, anchor="w")

    def go(action):
        saved_file.write_text(json.dumps({"layout": layout.get()}), encoding="utf-8")
        run(action, layout.get(), rebuild.get())

    for key, label in ACTIONS.items():
        tk.Button(win, text=label, width=28, command=lambda k=key: go(k)).pack(padx=16, pady=3)
    tk.Label(win, text="OBS must be open for Start and Build.", fg="gray").pack(pady=(6, 12))
    win.mainloop()


if __name__ == "__main__":
    main()
