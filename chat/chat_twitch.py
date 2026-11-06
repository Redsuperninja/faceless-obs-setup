"""Read Twitch chat anonymously (no login needed) over IRC."""

import socket
import ssl

HOST, PORT = "irc.chat.twitch.tv", 6697


def _split(line):
    """Break an IRC line into (tags, who, command, rest); None if it isn't a normal message line."""
    tags = {}
    if line.startswith("@"):
        raw, _, line = line[1:].partition(" ")
        for kv in raw.split(";"):
            k, _, v = kv.partition("=")
            tags[k] = v
    if not line.startswith(":"):
        return None
    who, _, rest = line[1:].partition(" ")
    cmd, _, rest = rest.partition(" ")
    return tags, who.split("!", 1)[0], cmd, rest


def _name(tags, fallback, key="display-name"):
    return tags.get(key, "").replace("\\s", " ") or fallback  # IRC writes a space as backslash-s


def parse_privmsg(line):
    """Turn one IRC line into a chat message dict, or None if it isn't chat."""
    parts = _split(line)
    if not parts or parts[2] != "PRIVMSG":
        return None
    tags, who, _, rest = parts
    text = rest.partition(" :")[2]
    if text.startswith("ACTION ") and text.endswith(""):
        text = text[8:-1]
    badges = tags.get("badges", "")
    return {"platform": "twitch", "user": _name(tags, who), "color": tags.get("color", ""),
            "text": text, "id": tags.get("id", ""),
            "mod": "moderator/" in badges or "broadcaster/" in badges}


def parse_alert(line):
    """Subs, gifts and raids (USERNOTICE lines) and cheers (a PRIVMSG with bits) as alert events."""
    parts = _split(line)
    if not parts:
        return None
    tags, who, cmd, _ = parts
    user = _name(tags, who)
    if cmd == "PRIVMSG" and tags.get("bits", "0") not in ("", "0"):
        return {"type": "alert", "kind": "bits", "user": user, "detail": tags["bits"], "platform": "twitch"}
    if cmd != "USERNOTICE":
        return None
    if tags.get("msg-param-community-gift-id"):
        return None  # one of a gift bomb: the single "gift bomb" card already covers it
    kind = {"sub": "sub", "resub": "resub", "subgift": "subgift", "anonsubgift": "subgift",
            "submysterygift": "giftbomb", "raid": "raid"}.get(tags.get("msg-id"))
    if not kind:
        return None
    if kind == "raid":
        user, detail = _name(tags, user, "msg-param-displayName"), tags.get("msg-param-viewerCount", "")
    elif kind == "resub":
        detail = tags.get("msg-param-cumulative-months", "")
    elif kind == "giftbomb":
        detail = tags.get("msg-param-mass-gift-count", "")
    else:
        detail = ""
    return {"type": "alert", "kind": kind, "user": user, "detail": detail, "platform": "twitch",
            "extra": _name(tags, "", "msg-param-recipient-display-name") or "a friend"}


def handle_line(line, publish, send):
    if line.startswith("PING"):
        send("PONG :tmi.twitch.tv")
        return
    msg = parse_privmsg(line)
    if msg:
        publish(msg)
    alert = parse_alert(line)
    if alert:
        publish(alert)


def run(channel, publish, stop, log=print):
    """Stay connected to one channel's chat until `stop` is set; reconnect on errors."""
    channel = channel.lstrip("#@").lower()
    ctx = ssl.create_default_context()
    while not stop.is_set():
        try:
            with socket.create_connection((HOST, PORT), timeout=30) as raw, \
                    ctx.wrap_socket(raw, server_hostname=HOST) as s:
                def send(text):
                    s.sendall((text + "\r\n").encode())
                s.settimeout(400)
                send("CAP REQ :twitch.tv/tags twitch.tv/commands")  # commands = sub/raid notices
                send("NICK justinfan48213")
                send(f"JOIN #{channel}")
                log(f"Twitch chat: joined #{channel}")
                buf = b""
                while not stop.is_set():
                    data = s.recv(4096)
                    if not data:
                        break
                    buf += data
                    while b"\r\n" in buf:
                        line, buf = buf.split(b"\r\n", 1)
                        handle_line(line.decode("utf-8", "replace"), publish, send)
        except OSError as e:
            log(f"Twitch chat: connection lost ({e}); retrying in 5s")
        stop.wait(5)
