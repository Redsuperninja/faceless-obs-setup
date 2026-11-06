"""Background music: find the tracks in media.music_dir and describe the playlist page for OBS."""

import urllib.parse
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
PLAYER_PAGE = (HERE / "web" / "music.html").as_uri()
AUDIO_EXT = {".mp3", ".ogg", ".wav", ".m4a", ".flac", ".opus"}


def playlist(cfg):
    """Names of the audio files in media.music_dir (empty if there is no folder or no tracks)."""
    folder = cfg["media"].get("music_dir")
    if not folder or not Path(folder).is_dir():
        return []
    return sorted(p.name for p in Path(folder).iterdir() if p.suffix.lower() in AUDIO_EXT)


def player_settings(cfg, files):
    """Browser-source settings that play `files` shuffled on a loop, through OBS's audio mixer."""
    query = urllib.parse.urlencode({
        "f": "|".join(files),
        "d": Path(cfg["media"]["music_dir"]).as_uri() + "/",
        "v": cfg["media"].get("music_volume", 1.0)})
    return {"url": f"{PLAYER_PAGE}?{query}", "width": 100, "height": 100, "css": "",
            "reroute_audio": True,   # show it in the Audio Mixer
            "shutdown": True,        # silent (and stopped) whenever its scene is not on screen
            "restart_when_active": False}
