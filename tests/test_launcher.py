import _paths  # noqa: F401
import unittest

import launcher


class LauncherCommands(unittest.TestCase):
    def test_horizontal_stream_skips_vertical_sync(self):
        self.assertIn("--no-vertical", launcher.command("stream", "horizontal"))
        self.assertNotIn("--no-vertical", launcher.command("stream", "both"))

    def test_build_passes_layout_and_reset(self):
        self.assertEqual(launcher.command("build", "horizontal", True, "py"),
                         ["py", "scripts/setup_obs.py", "--layout", "horizontal", "--reset"])
        self.assertNotIn("--reset", launcher.command("build", "both"))

    def test_chat_and_unknown(self):
        self.assertEqual(launcher.command("chat", "both", py="py"), ["py", "scripts/chat_hub.py"])
        with self.assertRaises(ValueError):
            launcher.command("nope", "both")


if __name__ == "__main__":
    unittest.main()
