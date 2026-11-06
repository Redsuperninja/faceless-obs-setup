"""Load KEY=VALUE lines from a local .env file into the environment (stdlib only).

Real environment variables win over the file. The .env file is git-ignored.
"""

import os
import sys
from pathlib import Path

DEFAULT = Path(__file__).resolve().parent.parent / ".env"


def load_env(path=DEFAULT):
    # Windows consoles often can't print the fancy letters in titles; never crash on them.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    path = Path(path)
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if value:  # a blank value means "not set"
            os.environ.setdefault(key.strip(), value)
