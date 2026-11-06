"""Stream output settings written into the OBS profile (Simple output mode): bitrate, encoder, scene transition."""

DEFAULT_KBPS = {"horizontal": 6000, "vertical": 4500}  # Twitch's own 1080p60 advice / 1080x1920 at 30fps
ENCODERS = {"cpu": "x264", "amd": "amd", "nvidia": "nvenc", "intel": "qsv"}  # config name -> OBS Simple-mode value


def apply_bitrate(cl, lay, encoder=""):
    """Set the profile's video bitrate (kbps) from the layout's "bitrate" setting and, if given, the encoder
    ("cpu", "amd", "nvidia" or "intel"; blank leaves it alone). Returns the bitrate used."""
    kbps = int(lay.get("bitrate", DEFAULT_KBPS["vertical" if lay["height"] > lay["width"] else "horizontal"]))
    params = [("Output", "Mode", "Simple"),
              ("SimpleOutput", "VBitrate", str(kbps)),
              ("SimpleOutput", "ABitrate", "160")]
    if encoder:
        params.append(("SimpleOutput", "StreamEncoder", ENCODERS[encoder]))
    for cat, name, value in params:
        cl.set_profile_parameter(cat, name, value)
    print(f"= video bitrate: {kbps} kbps" + (f", encoder: {encoder}" if encoder else "") + " (Simple output mode)")
    return kbps


def apply_transition(cl, cfg):
    """Make scene switches fade (config "transition": {"name": "Fade", "duration_ms": 500}; name "Cut" = none)."""
    t = cfg.get("transition", {"name": "Fade", "duration_ms": 500})
    cl.set_current_scene_transition(t["name"])
    if t["name"] != "Cut":
        cl.set_current_scene_transition_duration(int(t.get("duration_ms", 500)))
    print(f"= scene transition: {t['name']} {t.get('duration_ms', 500)} ms")
