import _paths  # noqa: F401
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from obs import flair  # noqa: E402



class Helpers(unittest.TestCase):
    def test_reads_image_size(self):
        import struct
        import tempfile
        png = bytes.fromhex("89504e470d0a1a0a0000000d49484452") + struct.pack(">II", 2560, 1440)
        with tempfile.TemporaryDirectory() as d:
            art = Path(d) / "art.png"
            art.write_bytes(png)
            self.assertEqual(flair.image_size(art), (2560, 1440))
        self.assertIsNone(flair.image_size(Path("missing.png")))

    def test_fit_box_hugs_the_picture_shape(self):
        b = SimpleNamespace(W=1920, H=1080)
        x, y, w, h = flair.Flair.fit_box(b, (0.0, 0.0, 0.32, 0.64), (2560, 1440), (26, 282, 1536, 32))
        picture = (2560 - 26 - 1536) / (1440 - 282 - 32)
        self.assertAlmostEqual((w * 1920) / (h * 1080), picture, places=3)
        self.assertLessEqual(w, 0.32 + 1e-9)
        self.assertLessEqual(h, 0.64 + 1e-9)

    def test_lighten_and_colors(self):
        self.assertEqual(flair.lighten("#000000", 1.0), "#FFFFFF")
        self.assertEqual(flair.hex_to_abgr("#FF0000", 0x80), 0x800000FF)


if __name__ == "__main__":
    unittest.main()
