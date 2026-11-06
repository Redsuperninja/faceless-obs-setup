import _paths  # noqa: F401
import json
import unittest

import chat_dock

INI = "[BasicWindow]\nExtraBrowserDocks=[]\nOther=1\n"


class DockTest(unittest.TestCase):
    def docks(self, text):
        line = next(ln for ln in text.splitlines() if ln.startswith("ExtraBrowserDocks="))
        return json.loads(line.split("=", 1)[1])

    def test_adds_one_dock_and_keeps_the_rest(self):
        out = chat_dock.add_dock(INI, "http://localhost:8765/?bg=1")
        self.assertEqual([d["title"] for d in self.docks(out)], [chat_dock.TITLE])
        self.assertIn("Other=1", out)

    def test_rerun_updates_instead_of_duplicating(self):
        once = chat_dock.add_dock(INI, "http://localhost:1/")
        twice = chat_dock.add_dock(once, "http://localhost:2/")
        docks = self.docks(twice)
        self.assertEqual(len(docks), 1)
        self.assertEqual(docks[0]["url"], "http://localhost:2/")


if __name__ == "__main__":
    unittest.main()
