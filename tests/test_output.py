import _paths  # noqa: F401
import unittest
from types import SimpleNamespace

from obs.output import apply_bitrate


class Fake:
    def __init__(self):
        self.calls = []

    def set_profile_parameter(self, cat, name, value):
        self.calls.append((cat, name, value))


class BitrateTest(unittest.TestCase):
    def test_uses_layout_setting(self):
        cl = Fake()
        self.assertEqual(apply_bitrate(cl, {"width": 1920, "height": 1080, "bitrate": 8000}), 8000)
        self.assertIn(("SimpleOutput", "VBitrate", "8000"), cl.calls)

    def test_defaults_by_orientation(self):
        self.assertEqual(apply_bitrate(Fake(), {"width": 1920, "height": 1080}), 6000)
        self.assertEqual(apply_bitrate(Fake(), {"width": 1080, "height": 1920}), 4500)


class ChatIconTest(unittest.TestCase):
    def test_chat_page_uses_logos_not_letters(self):
        html = open("web/chat.html", encoding="utf-8").read()
        self.assertNotIn('"TW"', html)
        self.assertIn(".twitch .b", html)
        self.assertIn("/logos/twitch.svg", html)
        self.assertIn("/logos/youtube.svg", html)


if __name__ == "__main__":
    unittest.main()
