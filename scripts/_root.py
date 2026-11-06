"""Import this first in a script: puts the project folder on the path so `chat`, `obs` and `accounts` import."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
