import _paths  # noqa: F401
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import mic_tune  # noqa: E402


def voice(level, n=60, peak_gap=10):
    return [(level + (i % 5) - 2, level + peak_gap) for i in range(n)]


class Tuning(unittest.TestCase):
    def test_too_little_talking_gives_no_answer(self):
        self.assertIsNone(mic_tune.analyse([(-95.0, -95.0)] * 100 + voice(-30, n=10)))

    def test_quiet_voice_gets_more_gain_than_loud_voice(self):
        quiet = mic_tune.analyse(voice(-40) + [(-95.0, -95.0)] * 40)
        loud = mic_tune.analyse(voice(-25) + [(-95.0, -95.0)] * 40)
        gain = lambda st: dict((n, s) for n, _, s in mic_tune.recommend(st))["Gain"]["db"]  # noqa: E731
        self.assertGreater(gain(quiet), gain(loud))
        self.assertEqual(gain(mic_tune.analyse(voice(-32) + [(-95.0, -95.0)] * 40)), 10.0)  # the measured example

    def test_gate_stays_below_quiet_words_on_a_noisy_mic(self):
        noisy = mic_tune.analyse(voice(-32) + [(-62.0, -50.0)] * 40)  # a real noise floor, not silence
        gate = dict((n, s) for n, _, s in mic_tune.recommend(noisy))["Noise Gate"]
        self.assertLess(gate["open_threshold"], noisy["soft"])
        self.assertLess(gate["close_threshold"], gate["open_threshold"])

    def test_chain_is_in_the_right_order(self):
        names = [n for n, _, _ in mic_tune.recommend(mic_tune.analyse(voice(-32) + [(-95.0, -95.0)] * 40))]
        self.assertEqual(names, ["Noise Suppression", "Noise Gate", "Gain", "Compressor", "Limiter"])


if __name__ == "__main__":
    unittest.main()
