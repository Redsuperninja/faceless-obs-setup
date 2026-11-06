import _paths  # noqa: F401
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from obs import layout  # noqa: E402


def overlaps(a, b):
    return a[0] < b[0] + b[2] - 1e-9 and b[0] < a[0] + a[2] - 1e-9 and a[1] < b[1] + b[3] - 1e-9 and b[1] < a[1] + a[3] - 1e-9


class Boxes(unittest.TestCase):
    def test_horizontal_panels_stack_in_the_sidebar_without_overlap(self):
        b = layout.boxes({}, 1920, 1080, False)
        self.assertAlmostEqual(b["deco"][2] * 1920 * 9 / 16, b["deco"][3] * 1080, places=3)  # art panel is 16:9
        stack = [b["deco"], b["goal"], b["chat"]]
        for i, a in enumerate(stack):
            for c in stack[i + 1:]:
                self.assertFalse(overlaps(a, c))
        self.assertFalse(overlaps(b["main"], b["sidebar"]))
        self.assertAlmostEqual(b["chat"][1] + b["chat"][3], b["sidebar"][1] + b["sidebar"][3])  # chat fills to the bottom

    def test_one_number_resizes_the_whole_column(self):
        narrow = layout.boxes({"layout": {"horizontal": {"sidebar_width": 0.20}}}, 1920, 1080, False)
        wide = layout.boxes({"layout": {"horizontal": {"sidebar_width": 0.30}}}, 1920, 1080, False)
        self.assertLess(narrow["chat"][2], wide["chat"][2])
        self.assertGreater(narrow["main"][2], wide["main"][2])  # the main area gives up the space

    def test_vertical_has_no_chat_and_overlays_sit_an_eighth_down_on_the_game(self):
        b = layout.boxes({}, 1080, 1920, True)
        self.assertIsNone(b["deco"])
        self.assertIsNone(b["chat"])  # Twitch draws its own chat over a vertical stream
        for name in ("plate", "goal"):
            self.assertAlmostEqual(b[name][1], 0.125)  # an eighth of the way down, clear of Twitch's top overlays
            self.assertTrue(overlaps(b[name], b["main"]))  # and sitting on the game
        self.assertFalse(overlaps(b["plate"], b["goal"]))

    def test_plain_column_has_no_art_panel_and_a_taller_chat(self):
        with_art = layout.boxes({}, 1920, 1080, False)
        plain = layout.boxes({}, 1920, 1080, False, deco=False)
        self.assertIsNone(plain["deco"])
        self.assertGreater(plain["chat"][3], with_art["chat"][3])
        self.assertEqual(plain["sidebar"], with_art["sidebar"])      # same column, same place
        self.assertEqual(plain["main"], with_art["main"])            # the capture area does not move
        self.assertAlmostEqual(plain["chat"][1] + plain["chat"][3], plain["sidebar"][1] + plain["sidebar"][3])


if __name__ == "__main__":
    unittest.main()
