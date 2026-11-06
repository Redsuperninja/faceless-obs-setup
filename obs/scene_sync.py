"""Keep the Aitum Vertical canvas on the same scene name as the main canvas.

Run while you stream (start_stream.py starts it for you):  python scene_sync.py
When you switch to "Gameplay" on the main canvas, the vertical canvas switches to its "Gameplay" too, so you
never link scenes by hand. Scenes with no vertical twin are ignored.
"""

import os
import threading

from accounts.env_loader import load_env

VENDOR = "aitum-vertical-canvas"


def sync_scene(req, name):
    """Switch the vertical canvas to `name`. Returns True if the plugin accepted it."""
    try:
        return bool(req.call_vendor_request(VENDOR, "switch_scene", {"scene": name}).response_data.get("success"))
    except Exception:  # noqa: BLE001  (no such vertical scene, or the plugin is not there)
        return False


def start(cfg):
    """Start listening in the background. Returns the event client (call .disconnect() to stop), or None."""
    try:
        import obsws_python as obs
    except ImportError:
        return None
    o = cfg["obs"]
    kw = dict(host=o["host"], port=o["port"], password=os.environ.get("OBS_WS_PASSWORD", o.get("password", "")), timeout=5)
    try:
        req, events = obs.ReqClient(**kw), obs.EventClient(**kw)
    except Exception as e:  # noqa: BLE001
        print(f"scene sync: could not reach OBS ({type(e).__name__}); vertical scenes will not follow the main ones")
        return None

    def on_current_program_scene_changed(data):  # obsws_python finds handlers by function name
        sync_scene(req, data.scene_name)

    events.callback.register(on_current_program_scene_changed)
    return events


def main():
    import json
    from pathlib import Path
    load_env()
    cfg = json.loads((Path(__file__).resolve().parent.parent / "config.json").read_text(encoding="utf-8"))
    if start(cfg):
        print("Vertical scenes now follow the main canvas. Ctrl+C to stop.")
        threading.Event().wait()


if __name__ == "__main__":
    main()
