"""Unicode "fonts": restyle plain text into double-struck, small capitals or Fraktur letters.

Only letters (and digits for double-struck) change; everything else passes through.
Which style each part of the stream uses is `fonts` in config.json.
"""

# U+2102 etc. are the "letterlike" characters; the rest of each alphabet is in the math block.
_DS_EXCEPTIONS = {"C": "ℂ", "H": "ℍ", "N": "ℕ", "P": "ℙ", "Q": "ℚ", "R": "ℝ", "Z": "ℤ"}
_FR_EXCEPTIONS = {"C": "ℭ", "H": "ℌ", "I": "ℑ", "R": "ℜ", "Z": "ℨ"}
_SMALL_CAPS = dict(zip("ABCDEFGHIJKLMNOPQRSTUVWXYZ", "ᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀꜱᴛᴜᴠᴡxʏᴢ"))  # no true small-cap X exists


def _math_alphabet(upper_start, lower_start, exceptions):
    def convert(ch):
        if ch in exceptions:
            return exceptions[ch]
        if "A" <= ch <= "Z":
            return chr(upper_start + ord(ch) - 65)
        if "a" <= ch <= "z":
            return chr(lower_start + ord(ch) - 97)
        return None
    return convert


_double = _math_alphabet(0x1D538, 0x1D552, _DS_EXCEPTIONS)
_fraktur = _math_alphabet(0x1D504, 0x1D51E, _FR_EXCEPTIONS)


def double_struck(text):
    """𝔻𝕠𝕦𝕓𝕝𝕖-𝕤𝕥𝕣𝕦𝕔𝕜 (digits too: 𝟘 to 𝟡)."""
    return "".join(_double(c) or (chr(0x1D7D8 + int(c)) if c.isascii() and c.isdigit() else c) for c in text)


def fraktur(text):
    """𝔉𝔯𝔞𝔨𝔱𝔲𝔯, the blackletter look."""
    return "".join(_fraktur(c) or c for c in text)


def small_caps(text):
    """ꜱᴍᴀʟʟ ᴄᴀᴘɪᴛᴀʟꜱ (lowercase and uppercase both become small capitals)."""
    return "".join(_SMALL_CAPS.get(c.upper(), c) if c.isalpha() and c.isascii() else c for c in text)


STYLES = {"double_struck": double_struck, "fraktur": fraktur, "small_caps": small_caps, "plain": lambda t: t}


def apply_style(name, text):
    """Restyle `text` with a named style; an unknown or empty name leaves it unchanged."""
    return STYLES.get(name or "plain", STYLES["plain"])(text)


def font_for(cfg, part):
    """The style name chosen for a part of the stream ("title", "chat", "alerts")."""
    return cfg.get("fonts", {}).get(part, "plain")
