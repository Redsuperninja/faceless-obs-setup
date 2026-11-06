"""Microphone, desktop sound and music ducking, kept in one shared "[S] Audio" scene.

The main scenes nest [S] Audio, so the mic and desktop sound are live in every scene without
touching OBS's global audio devices. Filters are added only if missing, so reruns are safe.
"""

from obs.names import S_AUDIO

MIC = "Mic (Stream)"
DESKTOP = "Desktop Audio (Stream)"
MUSIC = "BG Music"

# Voice chain, in order: remove steady background noise, close the gate on true silence, bring the
# voice up to a working level, even out quiet and loud words, then stop peaks clipping. These are
# starting values: `python mic_tune.py apply` re-tunes them to your own mic (and replaces these).
MIC_FILTERS = [
    ("Noise Suppression", "noise_suppress_filter_v2", {"method": "rnnoise"}),
    ("Noise Gate", "noise_gate_filter", {"open_threshold": -55.0, "close_threshold": -60.0,
                                          "attack_time": 10, "hold_time": 150, "release_time": 150}),
    ("Gain", "gain_filter", {"db": 10.0}),
    ("Compressor", "compressor_filter", {"ratio": 3.0, "threshold": -22.0, "attack_time": 8,
                                          "release_time": 120, "output_gain": 6.0}),
    ("Limiter", "limiter_filter", {"threshold": -2.0, "release_time": 60}),
]
# Music gets quieter while the mic is loud (a compressor listening to the mic) and recovers after.
DUCK = ("Duck Under Mic", "compressor_filter", {"sidechain_source": MIC, "ratio": 6.0, "threshold": -35.0,
                                                 "attack_time": 25, "release_time": 700, "output_gain": 0.0})
DESKTOP_DB = -8.0  # keep game/desktop sound under your voice


class Audio:
    saved_mic = None  # {"device": ..., "db": ...} read before a --reset

    def add_filters(self, source, filters):
        have = {f["filterName"] for f in self.cl.get_source_filter_list(source).filters}
        for name, kind, settings in filters:
            if name not in have:
                self.cl.create_source_filter(source, name, kind, settings)
                self.log(f"  + {source} filter: {name}")

    def build_audio(self):
        sc = S_AUDIO
        self.ensure_scene(sc)
        if self.canvas_mode:
            return  # the extra canvas uses the main audio mix
        if self.kind("mic"):
            existed = MIC in self.existing_inputs()
            self.ensure_item(sc, MIC, self.kind("mic"), {"device_id": "default"})
            self.add_filters(MIC, MIC_FILTERS)
            if not existed and self.saved_mic:  # a --reset must not undo the device and level you chose
                self.cl.set_input_settings(MIC, {"device_id": self.saved_mic["device"]}, True)
                self.cl.set_input_volume(MIC, vol_db=self.saved_mic["db"])
        else:
            self.log("  ! no microphone input type on this OBS; skipping the mic")
        if self.kind("desktop"):
            self.ensure_item(sc, DESKTOP, self.kind("desktop"), {"device_id": "default"})
            self.cl.set_input_volume(DESKTOP, vol_db=DESKTOP_DB)

    def duck_music(self):
        """Call after the scenes exist: only adds the filter if there is music to duck."""
        if MUSIC in self.existing_inputs() and MIC in self.existing_inputs():
            self.add_filters(MUSIC, [DUCK])
