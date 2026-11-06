"""Turn raw events (a raid, a sub, a chat command...) into cards the overlay page can show.

Readers publish small dicts like {"type": "alert", "kind": "raid", "user": "X", "detail": "12"};
decorate() adds the styled title and the sentence. Which letter style is used for alerts and for
commands comes from `fonts` in config.json (see textstyle.py).
"""

from pathlib import Path

from obs import textstyle

SOUNDS = Path(__file__).resolve().parent.parent / "assets" / "sounds"  # made by make_sounds.py

# kind -> (title, sentence). {user}, {detail} and {extra} are filled from the event.
ALERTS = {
    "sub": ("New Subscriber", "{user} joined the guild!"),
    "resub": ("Subscriber Returns", "{user} is {detail} months strong"),
    "subgift": ("Gifted Sub", "{user} gifted a sub to {extra}"),
    "giftbomb": ("Gift Bomb", "{user} gifted {detail} subs to the guild"),
    "raid": ("Raid!", "{user} arrives with {detail} raiders"),
    "bits": ("Cheer", "{user} cheered {detail} bits"),
    "superchat": ("Super Chat", "{user} sent {detail}"),
    "member": ("New Member", "{user} joined the guild"),
    "follow": ("New Follower", "{user} joined the guild"),
}


def sound_for(name, cfg):
    """The sound file for an alert kind (or "command"), unless sounds are off or the file is missing."""
    if not cfg.get("alerts", {}).get("sounds", True):
        return None
    return f"{name}.wav" if (SOUNDS / f"{name}.wav").exists() else None


def decorate(event, cfg):
    """Return the event with `title` and `text` filled in and styled (unknown events pass through)."""
    kind = event.get("type")
    fonts = cfg.get("fonts", {})
    if kind == "alert" and event.get("kind") in ALERTS:
        title, sentence = ALERTS[event["kind"]]
        text = sentence.format(user=event.get("user", "Someone"), detail=event.get("detail", ""),
                               extra=event.get("extra", "a friend"))
        if event.get("comment"):
            text += f': "{event["comment"]}"'
        return {**event, "title": textstyle.apply_style(fonts.get("alerts"), title), "text": text,
                "sound": sound_for(event["kind"], cfg)}
    if kind == "command":
        return {**event, "title": textstyle.apply_style(fonts.get("chat"), event.get("title", "")),
                "sound": sound_for("command", cfg)}
    return event
