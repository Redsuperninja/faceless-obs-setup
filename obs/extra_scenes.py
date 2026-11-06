"""Extra scenes: a big-chat "Just Chatting" scene and a private chat monitor."""

from obs.names import S_ALERTS, S_AUDIO, S_BACKGROUND, SCENE_CHATTING, SCENE_MONITOR
from obs.textstyle import apply_style, font_for


def popout_chat_url(cfg):
    """Twitch's own chat page for the channel (shows the real chat, with a login box)."""
    name = cfg["channel"].get("twitch_name", "").strip().lstrip("@")
    return f"https://www.twitch.tv/popout/{name}/chat?popout=" if name else ""


def print_chat_dock_help(cfg):
    url = popout_chat_url(cfg)
    print("\nTo read Twitch and YouTube chat together inside OBS: close OBS, run  python chat_dock.py, reopen OBS and")
    print("turn on View > Docks > 'Chat (Twitch + YouTube)' (start_stream.py fills it). For Twitch only instead:")
    print("Docks > Custom Browser Docks, add a dock named 'Chat' with")
    print(f"  URL: {url or 'https://www.twitch.tv/popout/<your-twitch-name>/chat?popout='}")
    if not url:
        print("  (set channel.twitch_name in config.json to fill this in)")
    print("Or right-click the 'Chat Monitor' scene > Windowed Projector (Scene) and put it on a second screen.")


class ExtraScenes:
    """Mixed into Builder; uses its helpers (ensure_scene, nest, place, ...)."""

    def build_chatting(self):
        """Face-free "Just Chatting": big chat, avatar, and the recent-events list."""
        sc = SCENE_CHATTING
        self.ensure_scene(sc)
        self.nest(sc, S_BACKGROUND, 0, 0, 1, 1)
        v = self.vertical
        title = self.cfg["channel"].get("title") or "LET'S CHAT"
        if v:  # no chat in the vertical layout (Twitch draws its own): big avatar and title, goal on the top row
            self.avatar(sc, (0.15, 0.30, 0.70, 0.42))
            self.heading(sc, apply_style(font_for(self.cfg, "title"), title), (0.05, 0.20, 0.90, 0.08))
            self.goal_panel(sc, self.layout_boxes()["goal"])
        else:
            self.chat_panel(sc, (0.40, 0.05, 0.57, 0.90))
            self.avatar(sc, (0.04, 0.20, 0.32, 0.64))
            self.heading(sc, apply_style(font_for(self.cfg, "title"), title), (0.02, 0.04, 0.36, 0.12))
            self.goal_panel(sc, (0.03, 0.18, 0.30, 0.10))
        self.nameplate(sc)
        self.music(sc)
        self.nest(sc, S_AUDIO, 0, 0, 1, 1)
        self.nest(sc, S_ALERTS, 0, 0, 1, 1)

    def build_chat_monitor(self):
        """Full-screen live chat for YOU (the combined chat box if set, else Twitch's own page). Don't switch to this scene while live."""
        sc = SCENE_MONITOR
        self.ensure_scene(sc)
        url = self.cfg["overlays"].get("chat_url") or popout_chat_url(self.cfg)
        item = self.ensure_item(sc, f"{sc} (browser)", self.kind("browser"),
                                self.browser(url, 1, 1))
        self.place(sc, item, 0, 0, 1, 1)
