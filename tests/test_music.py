import _paths  # noqa: F401
import sys
import tempfile
import unittest
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from obs import music  # noqa: E402


class Playlist(unittest.TestCase):
    def test_finds_only_audio_files_sorted(self):
        with tempfile.TemporaryDirectory() as d:
            for name in ("b track.mp3", "a.ogg", "notes.txt", "cover.png"):
                (Path(d) / name).write_bytes(b"x")
            cfg = {"media": {"music_dir": d}}
            self.assertEqual(music.playlist(cfg), ["a.ogg", "b track.mp3"])

    def test_no_folder_or_empty_means_no_music(self):
        self.assertEqual(music.playlist({"media": {}}), [])
        self.assertEqual(music.playlist({"media": {"music_dir": "nope-folder"}}), [])

    def test_player_settings_carry_files_folder_volume_and_audio_routing(self):
        with tempfile.TemporaryDirectory() as d:
            cfg = {"media": {"music_dir": d, "music_volume": 0.2}}
            s = music.player_settings(cfg, ["a.ogg", "b track.mp3"])
        q = urllib.parse.parse_qs(urllib.parse.urlparse(s["url"]).query)
        self.assertEqual((q["f"], q["v"]), (["a.ogg|b track.mp3"], ["0.2"]))
        self.assertTrue(q["d"][0].startswith("file:///") and q["d"][0].endswith("/"))
        self.assertTrue(s["reroute_audio"])


if __name__ == "__main__":
    unittest.main()
