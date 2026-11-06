"""Styling for the scenes: animated bordered cards, the chat panel, accent bars, name plate, mascot.

Mixed into Builder. Every decorative source is named "Deco ..." so --reset can find it.
Borders are drawn by frame.html (a small local web page) as browser sources, so they can
animate; the dark panels behind them are plain see-through color sources.
"""

import struct
import urllib.parse
from pathlib import Path

from obs.textstyle import apply_style, font_for

HERE = Path(__file__).resolve().parent.parent
FRAME_PAGE = (HERE / "web" / "frame.html").as_uri()


def hex_to_abgr(hex_color, alpha=0xFF):
    """OBS stores colors as 0xAABBGGRR integers."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return (alpha << 24) | (b << 16) | (g << 8) | r


def lighten(hex_color, amount=0.6):
    """Mix a color toward white (used for subtitles so they read on busy art)."""
    h = hex_color.lstrip("#")
    rgb = [int(h[i:i + 2], 16) for i in (0, 2, 4)]
    return "#" + "".join(f"{int(c + (255 - c) * amount):02X}" for c in rgb)


def resolve_media(cfg):
    """Let config.json use paths relative to this folder (e.g. assets/my-art.jpg)."""
    for key, value in cfg.get("media", {}).items():
        if isinstance(value, str) and value and not Path(value).is_absolute():
            cfg["media"][key] = str((HERE / value).resolve())


def image_size(path):
    """(width, height) of a PNG or JPEG, or None if it can't be read."""
    try:
        d = Path(path).read_bytes()
        if d[:8] == b"\x89PNG\r\n\x1a\n":
            return struct.unpack(">II", d[16:24])
        i = 2
        while d[:2] == b"\xff\xd8" and i < len(d):
            marker, length = d[i + 1], struct.unpack(">H", d[i + 2:i + 4])[0]
            if marker in (0xC0, 0xC1, 0xC2):
                h, w = struct.unpack(">HH", d[i + 5:i + 9])
                return w, h
            i += 2 + length
    except (OSError, struct.error, IndexError):
        pass
    return None


class Flair:
    def border_px(self):
        return max(8, int(min(self.W, self.H) * 0.011))

    def rect(self, scene, name, box, color, alpha=1.0):
        """A solid (optionally see-through) rectangle in a box given as canvas fractions."""
        x, y, w, h = box
        item = self.ensure_item(scene, name, self.kind("color"), {
            "color": hex_to_abgr(color, int(255 * alpha)),
            "width": max(1, int(w * self.W)), "height": max(1, int(h * self.H))})
        self.place(scene, item, x, y, w, h)
        return item

    def web(self, scene, name, box, **params):
        """A frame.html browser source (animated border / bar) filling a box."""
        x, y, w, h = box
        s = self.style
        query = urllib.parse.urlencode({
            "a": s["accent"], "b": s.get("accent2", s["accent"]), "c": s.get("accent3", s["accent"]),
            "t": self.border_px(), **params})
        item = self.ensure_item(scene, name, self.kind("browser"), {
            "url": f"{FRAME_PAGE}?{query}", "width": max(1, int(w * self.W)),
            "height": max(1, int(h * self.H)), "css": "",
            "shutdown": True,  # costs nothing while its scene isn't on screen
            "fps_custom": True, "fps": 30, "restart_when_active": False})
        self.place(scene, item, x, y, w, h)
        return item

    def ring(self, scene, tag, box, title=None, title_h=0.0, fill_alpha=0.0, gems=True):
        """Ornate frame (double line, corner flourishes, gems), optionally with a title and a
        dark gradient fill. Returns the inner box (fractions)."""
        x, y, w, h = box
        fx, fy = self.border_px() / self.W, self.border_px() / self.H
        extra = {"title": title, "th": int(title_h * self.H)} if title else {}
        if not gems or self.style.get("gems") is False:  # style.gems=false turns the diamonds off everywhere
            extra["gems"] = 0
        if fill_alpha:
            bg = self.style["background"]
            extra.update(fa=fill_alpha, f1=lighten(bg, 0.10), f2=bg)
        self.web(scene, f"Deco {tag} Frame", box, **extra)
        return (x + fx, y + fy, w - 2 * fx, h - 2 * fy)

    def card(self, scene, tag, box, alpha=0.8, title=None, title_h=0.0, gems=True):
        """Dark gradient panel with an ornate frame. Returns the inner box (fractions)."""
        return self.ring(scene, tag, box, title, title_h, fill_alpha=alpha, gems=gems)

    def frame(self, scene, tag, box):
        """An ornate frame just outside a box, for something sitting in that box."""
        x, y, w, h = box
        fx, fy = self.border_px() / self.W, self.border_px() / self.H
        self.ring(scene, tag, (x - fx, y - fy, w + 2 * fx, h + 2 * fy))

    def heading(self, scene, text, box):
        """A big metal-gradient heading drawn by the browser, so any letters work (even fancy ones)."""
        x, y, w, h = box
        size = int(min(h * self.H * 0.7, w * self.W / (max(1, len(text)) * 0.8)))
        self.web(scene, f"Deco {scene} Heading", box, m="text", title=text, size=size)

    def rule(self, scene, cx, y, w):
        """A short moving-gradient line, centered on cx."""
        self.web(scene, f"Deco {scene} Rule", (cx - w / 2, y, w, 0.007), m="bar")

    def edge_lines(self, scene):
        """Moving gradient lines around the canvas, per style.edge_lines: "none" (default),
        "all" (all four sides) or "top_bottom"."""
        mode = self.style.get("edge_lines", "none")
        if mode not in ("all", "top_bottom"):
            return
        self.web(scene, "Deco Edge Lines", (0, 0, 1, 1), m="edges", sides="all" if mode == "all" else "tb")

    def chat_panel(self, scene, box):
        """Chat in its own bordered panel with a LIVE CHAT header, sized exactly to the box
        (a nested scene would be shrunk and the text would be unreadable)."""
        label = self.cfg.get("chat", {}).get("title", "")  # blank = no header bar
        hh = (0.06 if not self.vertical else 0.04) if label else 0.0
        ix, iy, iw, ih = self.card(scene, f"{scene} Chat", box, alpha=(self.cfg.get("chat", {}).get("vertical_alpha", 0.3) if self.vertical else 0.82),
                                   title=apply_style(font_for(self.cfg, "chat"), label) if label else None, title_h=hh)
        css = ("body { background-color: rgba(0,0,0,0); margin: 0; overflow: hidden; "
               "box-sizing: border-box; padding: 0 10px 24px 10px; }")  # keep clear of the corner flourishes
        item = self.ensure_item(scene, f"Chat ({scene})", self.kind("browser"),
                                self.browser(self.chat_url(), iw, ih - hh, css))
        self.place(scene, item, ix, iy + hh, iw, ih - hh)

    def chat_url(self):
        """The chat page address; the vertical layout asks for bigger text (chat.html reads ?size=)."""
        url = self.cfg["overlays"].get("chat_url")
        size = self.cfg.get("chat", {}).get("vertical_font_px", 34)
        return f"{url}{'&' if '?' in url else '?'}size={size}" if url and self.vertical else url

    def goal_panel(self, scene, box):
        """A framed progress bar fed by goal.json (served by chat_hub at /goal)."""
        # No diamonds by default: they crowd a bar this short. Set goal_bar.gems to true in config.json to bring them back.
        gems = self.cfg.get("goal_bar", {}).get("gems", False)
        ix, iy, iw, ih = self.card(scene, f"{scene} Goal", box, alpha=0.82, gems=gems)
        port = self.cfg.get("chat", {}).get("port", 8765)
        item = self.ensure_item(scene, f"Goal ({scene})", self.kind("browser"),
                                self.browser(f"http://localhost:{port}/goal", iw, ih))
        self.place(scene, item, ix, iy, iw, ih)

    def nameplate(self, scene):
        """Channel name and handle in a small bordered plate along the bottom."""
        mx, my, mw, mh = self.layout_boxes()["main"]
        box = (mx, 1 - my - 0.07, 0.30, 0.07) if not self.vertical else self.layout_boxes()["plate"]
        # Plain like the goal bar: diamonds crowd a strip this short. nameplate.gems in config.json brings them back.
        gems = self.cfg.get("nameplate", {}).get("gems", False)
        ix, iy, iw, ih = self.card(scene, f"{scene} Plate", box, alpha=0.85, gems=gems)
        ch = self.cfg["channel"]
        label = "  |  ".join(p for p in (ch.get("name"), ch.get("handle")) if p)
        if self.vertical:  # the plate is small: handle only
            label = ch.get("handle") or label
        self.add_text(scene, f"Deco {scene} Plate Text", label,
                      0.028 if not self.vertical else 0.02, ix + iw / 2, iy + ih / 2)

    def fit_box(self, box, size, crop):
        """Shrink a box to the picture's shape (after cropping) so a frame hugs it."""
        if not size:
            return box
        l, t, r, b = crop or (0, 0, 0, 0)
        cw, ch = size[0] - l - r, size[1] - t - b
        if cw <= 0 or ch <= 0:
            return box
        x, y, w, h = box
        bw, bh = w * self.W, h * self.H
        pw, ph = (bh * cw / ch, bh) if bw / bh > cw / ch else (bw, bw * ch / cw)
        return (x + (w - pw / self.W) / 2, y + (h - ph / self.H) / 2, pw / self.W, ph / self.H)
