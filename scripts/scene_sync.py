#!/usr/bin/env python3
"""Runs obs.scene_sync (see its docstring: python scripts/scene_sync.py --help)."""
import _root  # noqa: F401  (puts the project folder on the path)
from obs.scene_sync import main

if __name__ == "__main__":
    main()
