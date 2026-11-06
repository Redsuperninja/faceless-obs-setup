"""Chat commands that pop a card up on stream, e.g. someone types !guild.

Defined in config.json under "commands": {"guild": {"title": "...", "text": "...",
"cooldown": 30, "mod_only": false}}. Nothing is sent back to chat; the card only shows on the stream.
A cooldown (seconds, per command) stops people spamming it.
"""

import time


class Commands:
    def __init__(self, definitions, clock=time.monotonic, global_cooldown=10):
        self.defs = {name.lower().lstrip("!"): d for name, d in (definitions or {}).items()}
        self.clock = clock
        self.last = {}
        self.global_cooldown = global_cooldown  # seconds between any two command cards
        self.last_any = -1e9

    def handle(self, msg):
        """Return a command event for a chat message, or None if it isn't one (or is cooling down)."""
        if msg.get("type") or not msg.get("text", "").startswith("!"):
            return None
        words = msg["text"][1:].split()
        cmd = self.defs.get(words[0].lower()) if words else None
        if not cmd or (cmd.get("mod_only") and not msg.get("mod")):
            return None
        now = self.clock()
        name = words[0].lower()
        if now - self.last_any < self.global_cooldown:
            return None
        if now - self.last.get(name, -1e9) < cmd.get("cooldown", 30):
            return None
        self.last[name] = now
        self.last_any = now
        return {"type": "command", "name": name, "title": cmd.get("title", name.upper()),
                "text": cmd.get("text", ""), "user": msg.get("user", "")}
