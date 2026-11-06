#!/usr/bin/env python3
"""
Tune the voice chain on "Mic (Stream)" to YOUR microphone (OBS must be open).

    python mic_tune.py measure   # listen ~25 s and print your levels; changes nothing
    python mic_tune.py apply     # measure, then set the filters from what it heard
    python mic_tune.py check     # listen with the filters ON to see what the stream gets

While it listens: stay quiet for the first 5 seconds, then talk at your normal live volume.
For `measure` and `apply` the filters are bypassed for the 25 seconds (so it hears your raw voice)
and always switched back on afterwards.

The chain it builds, in order: Noise Suppression, Noise Gate (just below your room's quiet),
Gain (brings your voice up to a working level), Compressor (evens out quiet and loud words),
Limiter (catches peaks). Levels are in dB; 0 is the loudest OBS can carry.
"""

import _root  # noqa: F401  (puts the project folder on the path)

import math
import os
import statistics
import sys
import time

from accounts import env_loader

MIC = "Mic (Stream)"
TARGET_RMS = -17.0   # where speech should sit on the stream (dB)
WORK_RMS = -22.0     # level the gain aims for, just under the compressor threshold
SPEECH_FLOOR = -55.0  # frames louder than this count as "talking"


def to_db(x):
    return -99.0 if x <= 1e-6 else 20 * math.log10(x)


def pct(values, p):
    values = sorted(values)
    return values[min(len(values) - 1, int(len(values) * p / 100))]


def analyse(samples):
    """samples = [(level_db, peak_db), ...] -> what your voice and your quiet look like."""
    speech = [(m, p) for m, p in samples if m > SPEECH_FLOOR]
    quiet = [m for m, _ in samples if m <= SPEECH_FLOOR]
    if len(speech) < 30:
        return None  # not enough talking to say anything
    mags = [m for m, _ in speech]
    return {
        "talking_share": len(speech) / len(samples),
        "median": statistics.median(mags), "loud": pct(mags, 90), "soft": pct(mags, 10),
        "peak_p95": pct([p for _, p in speech], 95), "peak_max": max(p for _, p in speech),
        "floor": statistics.median(quiet) if quiet else -99.0,
    }


def recommend(stats):
    """Filter settings that suit the measured voice."""
    gain = max(0, min(24, round(WORK_RMS - stats["median"])))
    if stats["floor"] <= -70:  # digital silence between words (e.g. the mic software gates it)
        gate_open, gate_close = -55.0, -60.0
    else:  # a real noise floor: open just above it, but never above your quiet words
        gate_open = min(stats["floor"] + 10, stats["soft"] - 6)
        gate_close = gate_open - 5
    return [
        ("Noise Suppression", "noise_suppress_filter_v2", {"method": "rnnoise"}),
        ("Noise Gate", "noise_gate_filter", {"open_threshold": gate_open, "close_threshold": gate_close,
                                              "attack_time": 10, "hold_time": 150, "release_time": 150}),
        ("Gain", "gain_filter", {"db": float(gain)}),
        ("Compressor", "compressor_filter", {"ratio": 3.0, "threshold": WORK_RMS, "attack_time": 8,
                                              "release_time": 120, "output_gain": TARGET_RMS - WORK_RMS + 1}),
        ("Limiter", "limiter_filter", {"threshold": -2.0, "release_time": 60}),
    ]


def listen(req, seconds, bypass):
    import obsws_python as obs
    samples = []

    def on_input_volume_meters(data):  # the name is how obsws-python knows which event this is
        for i in data.inputs:
            if i["inputName"] == MIC and i["inputLevelsMul"]:
                m, p = i["inputLevelsMul"][0][:2]
                samples.append((to_db(m), to_db(p)))

    filters = [(f["filterName"], f["filterEnabled"]) for f in req.get_source_filter_list(MIC).filters]
    ev = obs.EventClient(host="127.0.0.1", port=4455, password=os.environ["OBS_WS_PASSWORD"],
                         subs=obs.Subs.INPUTVOLUMEMETERS)
    ev.callback.register(on_input_volume_meters)
    try:
        if bypass:
            for name, _ in filters:
                req.set_source_filter_enabled(MIC, name, False)
        print(f"Listening for {seconds} s: quiet for 5 s, then talk normally...")
        time.sleep(seconds)
    finally:
        for name, was_on in filters:  # always put the filters back as they were
            req.set_source_filter_enabled(MIC, name, was_on)
        ev.disconnect()
    return samples


def apply_chain(req, chain):
    """Create missing filters, set every setting, and put them in order."""
    have = {f["filterName"] for f in req.get_source_filter_list(MIC).filters}
    for index, (name, kind, settings) in enumerate(chain):
        if name in have:
            req.set_source_filter_settings(MIC, name, settings, True)
        else:
            req.create_source_filter(MIC, name, kind, settings)
        req.set_source_filter_index(MIC, name, index)


def show(stats):
    print(f"  while talking: median {stats['median']:.1f} dB, loud words {stats['loud']:.1f}, soft words {stats['soft']:.1f}")
    print(f"  peaks: 95% of them under {stats['peak_p95']:.1f} dB, highest {stats['peak_max']:.1f} dB")
    print(f"  quiet between words: {stats['floor']:.1f} dB" + ("  (digital silence)" if stats['floor'] <= -70 else ""))


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode not in ("measure", "apply", "check"):
        sys.exit(__doc__)
    env_loader.load_env()
    import obsws_python as obs
    req = obs.ReqClient(host="127.0.0.1", port=4455, password=os.environ["OBS_WS_PASSWORD"], timeout=10)
    stats = analyse(listen(req, 25, bypass=mode != "check"))
    if not stats:
        sys.exit("I did not hear you talking. Check the mic device in OBS (is it muted, or the wrong one?) and try again.")
    print("What I heard:" if mode != "check" else "What the stream gets (filters on):")
    show(stats)
    if mode == "apply":
        chain = recommend(stats)
        apply_chain(req, chain)
        print("Set the voice chain:")
        for name, _, settings in chain:
            print(f"  {name}: {settings}")
        print("Run  python mic_tune.py check  to hear how it came out.")
    elif mode == "check":
        gap = stats["median"] - TARGET_RMS
        print(f"  target is about {TARGET_RMS:.0f} dB; you are {'right on it' if abs(gap) < 3 else f'{abs(gap):.0f} dB ' + ('too loud' if gap > 0 else 'too quiet')}")


if __name__ == "__main__":
    main()
