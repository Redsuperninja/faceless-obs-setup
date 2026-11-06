import _paths  # noqa: F401
import sys
import unittest
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from obs.flair import Flair  # noqa: E402


class FakeBuilder(Flair):
    """Just enough of the scene builder to see which settings the frames are given."""
    W, H, vertical = 1920, 1080, False

    def __init__(self, cfg, style):
        self.cfg, self.style, self.calls = cfg, style, []

    def kind(self, family):
        return "browser_source" if family == "browser" else "color_source_v3"

    def ensure_item(self, scene, name, kind, settings):
        self.calls.append((name, settings))
        return 1

    def place(self, *args, **kwargs):
        pass

    def browser(self, url, w, h, css=""):
        return {"url": url}

    def frame_query(self, name_part):
        url = [s["url"] for n, s in self.calls if name_part in n and "Frame" in n][0]
        return urllib.parse.parse_qs(urllib.parse.urlparse(url).query)


STYLE = {"accent": "#D5D9E3", "background": "#0E0E10"}


class Gems(unittest.TestCase):
    def test_goal_bar_has_no_diamonds_by_default_but_chat_does(self):
        b = FakeBuilder({}, STYLE)
        b.goal_panel("s", (0, 0, 0.2, 0.1))
        b.card("s", "Plain", (0, 0.2, 0.2, 0.3))
        self.assertEqual(b.frame_query("Goal").get("gems"), ["0"])
        self.assertNotIn("gems", b.frame_query("Plain"))

    def test_goal_bar_diamonds_can_be_switched_on(self):
        b = FakeBuilder({"goal_bar": {"gems": True}}, STYLE)
        b.goal_panel("s", (0, 0, 0.2, 0.1))
        self.assertNotIn("gems", b.frame_query("Goal"))

    def test_style_gems_false_turns_them_off_everywhere(self):
        b = FakeBuilder({}, {**STYLE, "gems": False})
        b.card("s", "Plain", (0, 0.2, 0.2, 0.3))
        self.assertEqual(b.frame_query("Plain").get("gems"), ["0"])

    def test_name_plate_is_plain_by_default_and_can_get_diamonds_back(self):
        plain = FakeBuilder({"channel": {"name": "N", "handle": "@h"}}, STYLE)
        plain.layout_boxes = lambda deco=True: {"main": (0.02, 0.036, 0.7, 0.93)}
        plain.add_text = lambda *a, **k: None
        plain.nameplate("Starting Soon")
        self.assertEqual(plain.frame_query("Plate").get("gems"), ["0"])
        fancy = FakeBuilder({"channel": {"name": "N", "handle": "@h"}, "nameplate": {"gems": True}}, STYLE)
        fancy.layout_boxes = plain.layout_boxes
        fancy.add_text = plain.add_text
        fancy.nameplate("Starting Soon")
        self.assertNotIn("gems", fancy.frame_query("Plate"))


if __name__ == "__main__":
    unittest.main()
