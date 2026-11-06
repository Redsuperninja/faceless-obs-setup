"""The right-hand column as one shared scene: [S] Sidebar = art panel + goal bar + chat.

Every main scene nests it at full size (1:1, so nothing is shrunk), which means the column is
built, edited and resized in one place. Sizes come from layout.py.
"""

from obs.layout import boxes
from obs.names import S_SIDEBAR, S_SIDEBAR_PLAIN
from obs.textstyle import apply_style, font_for


class Sidebar:
    def layout_boxes(self, deco=True):
        return boxes(self.cfg, self.W, self.H, self.vertical, deco)

    def build_sidebar(self):
        """Both versions of the column: with the art panel (S_SIDEBAR) and without (S_SIDEBAR_PLAIN)."""
        self.build_sidebar_scene(S_SIDEBAR, deco=True)
        self.build_sidebar_scene(S_SIDEBAR_PLAIN, deco=False)

    def build_sidebar_scene(self, sc, deco):
        self.ensure_scene(sc)
        b = self.layout_boxes(deco)
        if b["deco"]:
            self.deco_screen(sc, b["deco"])
        if b["goal"]:
            self.goal_panel(sc, b["goal"])
        if b["chat"]:  # the vertical layout has no chat: Twitch draws its own
            self.chat_panel(sc, b["chat"])

    def deco_screen(self, scene, box):
        """A framed panel showing the channel art with the show title across the bottom."""
        x, y, w, h = box
        art = self.cfg["media"].get("background_file")
        fx, fy = self.border_px() / self.W, self.border_px() / self.H
        inner = (x + fx, y + fy, w - 2 * fx, h - 2 * fy)
        self.rect(scene, "Deco Sidebar Backing", inner, self.style["background"])
        if art:
            item = self.ensure_item(scene, "Deco Sidebar Art", self.kind(self.media_kind_for(art)), {"file": art})
            self.place(scene, item, *inner)
        ix, iy, iw, ih = inner
        # A dark band so the title reads over the picture.
        self.rect(scene, "Deco Sidebar Scrim", (ix, iy + ih * 0.70, iw, ih * 0.30), "#000000", 0.6)
        # The panel text: deco.title in config.json, else the show title. Change it to whatever you like.
        title = self.cfg.get("deco", {}).get("title") or self.cfg["channel"].get("title")
        if title:
            self.heading(scene, apply_style(font_for(self.cfg, "title"), title),
                         (ix + iw * 0.04, iy + ih * 0.71, iw * 0.92, ih * 0.28))
        self.ring(scene, "Sidebar Art", box)
