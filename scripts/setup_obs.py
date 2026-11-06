#!/usr/bin/env python3
"""
Build a full set of OBS scenes for a faceless (no webcam) stream.

Talks to OBS Studio 28+ over its built-in WebSocket server (protocol v5).
Creates its own profile and scene collection, so your existing setup is
left alone.

    python setup_obs.py                      # 16:9 Twitch/YouTube layout
    python setup_obs.py --layout vertical    # 9:16 TikTok layout
    python setup_obs.py --dry-run            # print what would happen
    python setup_obs.py --reset              # rebuild scenes from scratch

Secrets come from environment variables, never from config.json:
    OBS_WS_PASSWORD     OBS WebSocket password (Tools > WebSocket Server Settings)
    TWITCH_STREAM_KEY   optional, sets the Twitch stream key on the horizontal profile
    TIKTOK_RTMP_URL     optional, TikTok server URL for the vertical profile
    TIKTOK_STREAM_KEY   optional, TikTok stream key for the vertical profile
"""

import _root  # noqa: F401  (puts the project folder on the path)

import argparse
import json
import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace

from accounts.env_loader import load_env

HERE = Path(__file__).resolve().parent.parent
load_env()

from obs.names import *  # noqa: F401,F403  (scene names)
from obs.extra_scenes import ExtraScenes, print_chat_dock_help
from obs.flair import Flair, hex_to_abgr, image_size, lighten, resolve_media
from obs.audio import Audio
from obs.canvas import SUFFIX, CanvasClient, find_canvas, main_has_input, release_shared
from obs.output import apply_bitrate, apply_transition
from obs.sidebar import Sidebar
from obs.music import playlist, player_settings
from obs.textstyle import apply_style, font_for

# Input kinds differ by OS and OBS version, so we try candidates in order and
# use the first one this OBS actually has.
KINDS = {
    "color": ["color_source_v3", "color_source_v2", "color_source"],
    "text": ["text_gdiplus_v3", "text_gdiplus_v2", "text_gdiplus",
             "text_ft2_source_v2", "text_ft2_source"],
    "browser": ["browser_source"],
    "image": ["image_source"],
    "media": ["ffmpeg_source"],
    "game": ["game_capture"],  # Windows only
    "mic": ["wasapi_input_capture", "coreaudio_input_capture", "pulse_input_capture"],
    "desktop": ["wasapi_output_capture", "coreaudio_output_capture", "pulse_output_capture"],
    "display": ["monitor_capture", "screen_capture", "display_capture",
                "pipewire-desktop-capture-source", "xshm_input"],
}

MUSIC_START_DB = -14.0  # first volume of the BG Music slider; adjust it in the OBS mixer
VIDEO_EXT = {".mp4", ".mov", ".webm", ".mkv", ".gif"}


class DryRunClient:
    """Stands in for obsws_python.ReqClient and prints each request."""

    def __init__(self):
        self.ids = 0

    def get_input_kind_list(self, unversioned):
        return SimpleNamespace(input_kinds=sorted({k for v in KINDS.values() for k in v}))

    def get_scene_list(self):
        return SimpleNamespace(scenes=[], current_program_scene_name="")

    def get_input_list(self, kind=None):
        return SimpleNamespace(inputs=[])

    def get_scene_item_list(self, name):
        return SimpleNamespace(scene_items=[])

    def get_source_filter_list(self, name):
        return SimpleNamespace(filters=[])

    def get_scene_collection_list(self):
        return SimpleNamespace(scene_collections=[], current_scene_collection_name="")

    def get_profile_list(self):
        return SimpleNamespace(profiles=[], current_profile_name="")

    def __getattr__(self, name):
        def call(*args, **kwargs):
            shown = ", ".join([repr(a) for a in args] +
                              [f"{k}={v!r}" for k, v in kwargs.items()])
            if len(shown) > 160:
                shown = shown[:157] + "..."
            print(f"  [dry-run] {name}({shown})")
            self.ids += 1
            return SimpleNamespace(scene_item_id=self.ids)
        return call


class Builder(ExtraScenes, Flair, Audio, Sidebar):
    def __init__(self, client, cfg, layout, verbose=True):
        self.cl = client
        self.cfg = cfg
        self.layout = layout
        lay = cfg["layouts"][layout]
        self.W, self.H = lay["width"], lay["height"]
        self.vertical = layout == "vertical"
        self.verbose = verbose
        self.kinds = set(client.get_input_kind_list(False).input_kinds)
        self.style = cfg["style"]
        self.canvas_mode = getattr(client, "is_canvas", False)  # building into an extra canvas

    # ---------- helpers ----------
    def log(self, msg):
        if self.verbose:
            print(msg)

    def kind(self, family):
        for k in KINDS[family]:
            if k in self.kinds:
                return k
        return None

    def existing_scenes(self):
        return {s["sceneName"] for s in self.cl.get_scene_list().scenes}

    def existing_inputs(self):
        return {i["inputName"] for i in self.cl.get_input_list().inputs}

    def scene_items(self, scene):
        return {i["sourceName"]: i["sceneItemId"]
                for i in self.cl.get_scene_item_list(scene).scene_items}

    def ensure_scene(self, name):
        if name in self.existing_scenes():
            self.log(f"= scene exists: {name}")
        else:
            self.cl.create_scene(name)
            self.log(f"+ scene: {name}")

    def ensure_item(self, scene, source, kind=None, settings=None):
        """Put `source` into `scene`, creating the input if it doesn't exist.
        Returns the scene item id, or None if the source can't be made here."""
        items = self.scene_items(scene)
        if source in items:
            return items[source]
        if kind is None or source in self.existing_inputs() or source in self.existing_scenes():
            item_id = self.cl.create_scene_item(scene, source, True).scene_item_id
        else:
            item_id = self.cl.create_input(scene, source, kind, settings or {}, True).scene_item_id
        self.log(f"  + {scene} <- {source}")
        return item_id

    def place(self, scene, item_id, x, y, w, h, crop=None, bounds="OBS_BOUNDS_SCALE_INNER"):
        """Fit an item into a box given as fractions of the canvas."""
        if item_id is None:
            return
        t = {
            "positionX": x * self.W, "positionY": y * self.H,
            "alignment": 5,  # top-left
            "boundsType": bounds,
            "boundsAlignment": 0,
            "boundsWidth": max(1.0, w * self.W), "boundsHeight": max(1.0, h * self.H),
        }
        if crop:
            t.update(crop)
        self.cl.set_scene_item_transform(scene, item_id, t)

    def center(self, scene, item_id, x, y):
        if item_id is None:
            return
        self.cl.set_scene_item_transform(scene, item_id, {
            "positionX": x * self.W, "positionY": y * self.H,
            "alignment": 0, "boundsType": "OBS_BOUNDS_NONE",
        })

    def text_settings(self, text, size_frac, color=None):
        kind = self.kind("text")
        size = int(self.H * size_frac) if not self.vertical else int(self.W * size_frac * 1.2)
        color_val = hex_to_abgr(color or self.style["text"])
        font = {"face": self.style["font"], "size": size, "style": "Bold", "flags": 1}
        if kind and kind.startswith("text_gdiplus"):
            s = {"text": text, "font": font, "color": color_val, "align": "center",
                 "outline": True, "outline_size": max(2, size // 20),
                 "outline_color": hex_to_abgr("#000000")}
        else:
            s = {"text": text, "font": font, "color1": color_val, "color2": color_val,
                 "outline": True, "drop_shadow": True}
        return kind, s

    def add_text(self, scene, name, text, size_frac, x, y, color=None):
        kind, s = self.text_settings(text, size_frac, color)
        if not kind:
            self.log(f"  ! no text source available, skipping {name}")
            return None
        item = self.ensure_item(scene, name, kind, s)
        self.center(scene, item, x, y)
        return item

    def browser(self, url, w, h, css=""):
        return {"url": url or "about:blank", "width": int(w * self.W),
                "height": int(h * self.H), "css": css,
                "shutdown": False, "restart_when_active": False}

    def media_kind_for(self, path):
        return "media" if Path(path).suffix.lower() in VIDEO_EXT else "image"

    # ---------- building blocks ----------
    def build_background(self):
        sc = S_BACKGROUND
        self.ensure_scene(sc)
        bg = self.cfg["media"].get("background_file")
        if bg:
            fam = self.media_kind_for(bg)
            settings = ({"local_file": bg, "looping": True, "restart_on_activate": False}
                        if fam == "media" else {"file": bg})
            item = self.ensure_item(sc, "Background Media", self.kind(fam), settings)
            self.place(sc, item, 0, 0, 1, 1, bounds="OBS_BOUNDS_SCALE_OUTER")  # cover, crop the overflow
            # Darken the art so titles and chat stay readable (style.dim, 0 to 1).
            self.rect(sc, "Deco Background Dim", (0, 0, 1, 1), "#000000", self.style.get("dim", 0.5))
        else:
            item = self.ensure_item(sc, "Background Color", self.kind("color"), {
                "color": hex_to_abgr(self.style["background"]),
                "width": self.W, "height": self.H})
            self.place(sc, item, 0, 0, 1, 1)
        # Moving gradient lines along the top and bottom, so plain backgrounds don't look empty.
        self.edge_lines(sc)

    def build_alerts(self):
        sc = S_ALERTS
        self.ensure_scene(sc)
        url = self.cfg["overlays"].get("alerts_url")
        settings = self.browser(url, 1, 1)
        if url and "/overlay" in url:  # our own overlay: centre cards over the main area; the extra canvas stays silent
            mx, _, mw, _ = self.layout_boxes()["main"]
            settings["url"] = f"{url}?x={mx + mw / 2:.3f}" + ("&sound=0" if self.canvas_mode else "")
        settings["reroute_audio"] = True  # alert sounds appear as "Alerts (browser)" in the OBS mixer
        item = self.ensure_item(sc, "Alerts (browser)", self.kind("browser"), settings)
        self.place(sc, item, 0, 0, 1, 1)
        ev = self.cfg["overlays"].get("event_list_url")
        if ev:
            box = (0.02, 0.02, 0.22, 0.30) if not self.vertical else (0.03, 0.02, 0.5, 0.15)
            item = self.ensure_item(sc, "Recent Events (browser)", self.kind("browser"),
                                    self.browser(ev, box[2], box[3]))
            self.place(sc, item, *box)

    def nest(self, scene, child, x, y, w, h):
        item = self.ensure_item(scene, child)
        self.place(scene, item, x, y, w, h)
        return item

    def music(self, scene):
        self.nest(scene, S_MUSIC, 0, 0, 1, 1)

    saved_music_db = None  # the volume you had set before a --reset, put back afterwards

    def build_music(self):
        """Music lives in its own shared scene, so there is one slider (BG Music) in the OBS mixer."""
        self.ensure_scene(S_MUSIC)
        if self.canvas_mode:
            return  # the extra canvas uses the main audio mix
        files, path = playlist(self.cfg), self.cfg["media"].get("music_file")
        if files:  # every track in media.music_dir, shuffled
            kind, settings = self.kind("browser"), player_settings(self.cfg, files)
        elif path:  # or one looping file
            kind, settings = self.kind("media"), {"local_file": path, "looping": True,
                                                  "restart_on_activate": False, "close_when_inactive": False}
        else:
            return
        existed = "BG Music" in self.existing_inputs()
        self.ensure_item(S_MUSIC, "BG Music", kind, settings)
        if not existed:  # first time (or after a reset): start quiet, you take it from there
            keep = self.saved_music_db not in (None, 0.0)  # 0 dB is just OBS's default, not a choice
            db = self.saved_music_db if keep else MUSIC_START_DB
            self.cl.set_input_volume("BG Music", vol_db=db)

    def avatar(self, scene, box):
        path = self.cfg["media"].get("avatar_image")
        if not path:
            return
        fam = self.media_kind_for(path)
        settings = ({"local_file": path, "looping": True} if fam == "media" else {"file": path})
        # avatar_crop = [left, top, right, bottom] pixels to trim, e.g. to pick a mascot out of art.
        crop = self.cfg["media"].get("avatar_crop")
        box = self.fit_box(box, image_size(path) if fam == "image" else None, crop)
        self.frame(scene, f"{scene} Avatar", box)
        item = self.ensure_item(scene, "Avatar", self.kind(fam), settings)
        names = ("cropLeft", "cropTop", "cropRight", "cropBottom")
        self.place(scene, item, *box, crop=dict(zip(names, crop)) if crop else None)

    def capture(self, scene, prefer_game):
        """Game Capture on Windows, otherwise a display capture."""
        name = "Game Capture" if prefer_game and self.kind("game") else "Display Capture"
        if getattr(self.cl, "is_canvas", False) is True and main_has_input(self.cl.cl, name):
            # Vertical canvas: reuse the main canvas's capture. A second game capture cannot hook the same game.
            items = self.scene_items(scene)
            if name in items:
                return items[name]
            self.log(f"  + {scene} <- {name} (shared with the main canvas)")
            return self.cl.create_scene_item(scene, name, True).scene_item_id
        if prefer_game and self.kind("game"):
            return self.ensure_item(scene, "Game Capture", self.kind("game"),
                                    {"capture_mode": "any_fullscreen",
                                     "capture_cursor": False, "allow_transparency": False})
        kind = self.kind("display")
        if not kind:
            self.log("  ! no display capture available on this OBS")
            return None
        return self.ensure_item(scene, "Display Capture", kind, {})

    # ---------- main scenes ----------
    def holding_scene(self, scene, title, subtitle, with_chat=True, deco=True):
        """Shared layout for Starting Soon / BRB / Ending: a title card in the main area.
        deco=False uses the right-hand column without the art panel."""
        self.ensure_scene(scene)
        self.nest(scene, S_BACKGROUND, 0, 0, 1, 1)
        v = self.vertical
        if with_chat:
            self.nest(scene, S_SIDEBAR if deco else S_SIDEBAR_PLAIN, 0, 0, 1, 1)
        mx, my, mw, mh = self.layout_boxes(deco)["main"] if with_chat else (0, 0, 1, 1)
        tx = mx + mw / 2
        cy = my + mh / 2
        cw, ch = (mw * 0.9 if with_chat else 0.58, 0.40) if not v else (mw, 0.24)
        ty = cy + (-0.07 if not v else -0.01)
        self.card(scene, f"{scene} Title Card", (tx - cw / 2, cy - ch / 2, cw, ch), alpha=0.8)
        # Drawn by the browser (frame.html) so the fancy letters render; styled per config "fonts".
        self.heading(scene, apply_style(font_for(self.cfg, "title"), title),
                     (tx - cw * 0.47, ty - 0.07, cw * 0.94, 0.14) if not v else (tx - cw * 0.47, ty - 0.05, cw * 0.94, 0.10))
        self.rule(scene, tx, ty + (0.052 if not v else 0.034), 0.30 if not v else 0.5)
        self.add_text(scene, f"{scene} Subtitle", subtitle, 0.035, tx, ty + (0.11 if not v else 0.07),
                      color=lighten(self.style.get("accent2", self.style["accent"]), 0.3))
        self.nameplate(scene)
        self.music(scene)
        self.nest(scene, S_AUDIO, 0, 0, 1, 1)
        self.nest(scene, S_ALERTS, 0, 0, 1, 1)

    def capture_scene(self, scene, prefer_game, deco):
        """Gameplay or Display: the capture in the main area (kept 16:9, framed), sidebar on the right.
        deco=True uses the column with the art panel (the slot for an avatar or face cam)."""
        self.ensure_scene(scene)
        self.nest(scene, S_BACKGROUND, 0, 0, 1, 1)
        if not self.vertical:
            self.nest(scene, S_SIDEBAR if deco else S_SIDEBAR_PLAIN, 0, 0, 1, 1)
        main = self.layout_boxes(deco)["main"]
        # Vertical: fill the tall box (centre of the picture, edges cropped) so the game is big, not a thin strip.
        box = main if self.vertical else self.fit_box(main, (16, 9), None)
        if not self.vertical:  # vertical: the game fills its box with no ornate frame
            self.frame(scene, scene, box)
        self.place(scene, self.capture(scene, prefer_game=prefer_game), *box,
                   bounds="OBS_BOUNDS_SCALE_OUTER" if self.vertical else "OBS_BOUNDS_SCALE_INNER")
        if self.vertical:  # the goal bar overlays the game, so it is added after (above) the capture
            self.nest(scene, S_SIDEBAR if deco else S_SIDEBAR_PLAIN, 0, 0, 1, 1)
            self.nameplate(scene)
        self.nest(scene, S_AUDIO, 0, 0, 1, 1)
        self.nest(scene, S_ALERTS, 0, 0, 1, 1)

    def build_capture_scenes(self):
        self.capture_scene(SCENE_GAMEPLAY, prefer_game=True, deco=False)
        self.capture_scene(SCENE_DISPLAY, prefer_game=False, deco=False)
        if not self.vertical:  # the vertical layout has no art panel, so these would be duplicates
            self.capture_scene(SCENE_GAMEPLAY_CAM, prefer_game=True, deco=True)
            self.capture_scene(SCENE_DISPLAY_CAM, prefer_game=False, deco=True)

    def build_all(self):
        ch = self.cfg["channel"]
        self.log(f"Building {self.layout} scenes at {self.W}x{self.H}")
        self.build_background()
        self.build_alerts()
        self.build_audio()
        self.build_music()
        self.build_sidebar()
        self.holding_scene(SCENE_STARTING, "STARTING SOON", ch.get("tagline", ""), deco=False)
        if not self.vertical:  # the vertical layout has no art panel, so it would be a duplicate
            self.holding_scene(SCENE_STARTING_CAM, "STARTING SOON", ch.get("tagline", ""))
        self.build_capture_scenes()
        self.build_chatting()
        self.build_chat_monitor()
        self.holding_scene(SCENE_BRB, "BE RIGHT BACK", "Grab a snack, I'll be back soon")
        self.holding_scene(SCENE_ENDING, "THANKS FOR WATCHING",
                           f"Follow {ch.get('handle', '')} on Twitch, YouTube & TikTok",
                           with_chat=False)
        self.duck_music()
        self.cl.set_current_program_scene(SCENE_STARTING)

    def reset(self):
        try:  # keep the music volume you set in the mixer across a rebuild
            self.saved_music_db = self.cl.get_input_volume("BG Music").input_volume_db
        except Exception:  # noqa: BLE001  (no music yet, or a dry run)
            pass
        try:  # and keep the microphone you picked (and its level) across a rebuild
            self.saved_mic = {"device": self.cl.get_input_settings("Mic (Stream)").input_settings["device_id"],
                              "db": self.cl.get_input_volume("Mic (Stream)").input_volume_db}
        except Exception:  # noqa: BLE001  (no mic source yet, or a dry run)
            pass
        existing = self.existing_scenes()
        for s in ALL_SCENES:
            if s in existing:
                self.cl.remove_scene(s)
                self.log(f"- removed scene {s}")
        # Inputs that are no longer in any scene stay around as orphans; remove ours.
        ours_prefixes = ("Background ", "Accent Stripe", "Alerts (", "Recent Events (",
                         "Chat (", "BG Music", "Avatar", "Game Capture", "Display Capture",
                         "Gameplay Handle", "Deco ", "Goal (", "Mic (", "Desktop Audio (") + tuple(f"{s} " for s in ALL_SCENES)
        def mine(name):  # the main canvas must never remove the extra canvas's "(V)" sources
            return name.startswith(ours_prefixes) and (self.canvas_mode or not name.endswith(SUFFIX))

        for name in self.existing_inputs():
            if mine(name):
                self.cl.remove_input(name)
                self.log(f"- removed input {name}")
        # OBS finishes removing sources a moment later; building before then can trip over
        # a source that is listed but already going away. Wait until the lists are clean.
        for _ in range(40):
            left = [n for n in self.existing_inputs() if mine(n)]
            if not left and not set(ALL_SCENES) & self.existing_scenes():
                return
            time.sleep(0.25)
        self.log("! some old sources are still being removed; if the build fails, run it again")


def switch_profile_and_collection(cl, cfg, layout, dry, target=""):
    lay = cfg["layouts"][layout]
    prof, coll = lay["profile"], lay["collection"]

    profiles = cl.get_profile_list()
    if prof not in getattr(profiles, "profiles", []):
        cl.create_profile(prof)  # also switches to it
        print(f"+ profile: {prof}")
    elif profiles.current_profile_name != prof:
        cl.set_current_profile(prof)
    colls = cl.get_scene_collection_list()
    if coll not in getattr(colls, "scene_collections", []):
        cl.create_scene_collection(coll)  # also switches to it
        print(f"+ scene collection: {coll}")
    elif colls.current_scene_collection_name != coll:
        cl.set_current_scene_collection(coll)
    if not dry:
        time.sleep(2)  # OBS finishes loading the collection asynchronously

    fps = int(lay.get("fps", 60))
    cl.set_video_settings(fps, 1, lay["width"], lay["height"], lay["width"], lay["height"])
    print(f"= video: {lay['width']}x{lay['height']} @ {fps}fps")

    apply_bitrate(cl, lay, cfg.get("output", {}).get("encoder", ""))
    apply_transition(cl, cfg)
    twitch_here = layout == "horizontal" or target == "twitch"
    if twitch_here and os.environ.get("TWITCH_STREAM_KEY"):
        cl.set_stream_service_settings("rtmp_common", {
            "service": "Twitch", "server": "auto", "key": os.environ["TWITCH_STREAM_KEY"]})
        print("= stream output: Twitch (key from TWITCH_STREAM_KEY)")
    if layout == "vertical" and target != "twitch" and os.environ.get("TIKTOK_RTMP_URL") and os.environ.get("TIKTOK_STREAM_KEY"):
        cl.set_stream_service_settings("rtmp_custom", {
            "server": os.environ["TIKTOK_RTMP_URL"], "key": os.environ["TIKTOK_STREAM_KEY"],
            "use_auth": False})
        print("= stream output: TikTok custom RTMP (from TIKTOK_RTMP_URL / TIKTOK_STREAM_KEY)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=str(HERE / "config.json"))
    ap.add_argument("--layout", choices=["horizontal", "vertical", "both"], default="both",
                    help="both (default): 16:9 for Twitch/YouTube, then 9:16 into the Aitum Vertical canvas")
    ap.add_argument("--dry-run", action="store_true", help="print requests instead of talking to OBS")
    ap.add_argument("--reset", action="store_true", help="delete these scenes first, then rebuild")
    ap.add_argument("--canvas", metavar="NAME",
                    help='build into an extra OBS canvas such as "Aitum Vertical" (use with --layout vertical)')
    ap.add_argument("--target", choices=["twitch", "tiktok"], default="",
                    help="where the vertical profile streams (default: TikTok if its env vars are set); "
                         "twitch uses TWITCH_STREAM_KEY")
    ap.add_argument("--no-profile", action="store_true",
                    help="build into whatever profile/collection is open now and leave video settings alone")
    args = ap.parse_args()

    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    resolve_media(cfg)

    if args.dry_run:
        cl = DryRunClient()
    else:
        try:
            import obsws_python as obs
        except ImportError:
            sys.exit("Missing dependency: run  pip install -r requirements.txt")
        o = cfg["obs"]
        try:
            cl = obs.ReqClient(host=o["host"], port=o["port"],
                               password=os.environ.get("OBS_WS_PASSWORD", o.get("password", "")),
                               timeout=10)
        except Exception as e:  # noqa: BLE001
            sys.exit(f"Could not connect to OBS at {o['host']}:{o['port']}: {e}\n"
                     "Open OBS, enable Tools > WebSocket Server Settings, and check the password.")

    canvas_name = args.canvas or cfg["obs"].get("vertical_canvas", "Aitum Vertical")
    if args.reset and args.layout == "both" and not args.dry_run:
        extra = find_canvas(cl, canvas_name)
        if extra:
            release_shared(cl, extra[0])
    if args.layout in ("horizontal", "both"):
        if not args.no_profile:
            switch_profile_and_collection(cl, cfg, "horizontal", args.dry_run, args.target)
        build(cl, cfg, "horizontal", args.reset)
    if args.layout in ("vertical", "both"):
        vcl = vertical_client(cl, cfg, canvas_name, args)
        if vcl:
            build(vcl, cfg, "vertical", args.reset)
    print_chat_dock_help(cfg)
    print("\nDone. Check the new scenes in OBS, then fill in any blank browser-source URLs.")


def build(cl, cfg, layout, reset):
    b = Builder(cl, cfg, layout)
    if reset:
        b.reset()
    b.build_all()


def vertical_client(cl, cfg, canvas_name, args):
    """The client that writes vertical scenes: the extra canvas if OBS has it, else (vertical only) its own profile."""
    if args.dry_run:
        return cl
    found = find_canvas(cl, canvas_name)
    if found:
        uuid, video = found
        lay = cfg["layouts"]["vertical"]
        if (video["baseWidth"], video["baseHeight"]) != (lay["width"], lay["height"]):
            sys.exit(f"That canvas is {video['baseWidth']}x{video['baseHeight']} but config.json's vertical layout is "
                     f"{lay['width']}x{lay['height']}; make them match first.")
        return CanvasClient(cl, uuid)  # scenes go into that canvas; the main canvas is never touched
    if args.canvas or args.layout == "both":
        print(f"! No canvas called {canvas_name!r} in OBS (install/enable Aitum Vertical): skipped the vertical scenes. "
              "For a separate vertical profile run:  setup_obs.py --layout vertical")
        return None
    if not args.no_profile:
        switch_profile_and_collection(cl, cfg, "vertical", False, args.target)
    return cl


if __name__ == "__main__":
    main()
