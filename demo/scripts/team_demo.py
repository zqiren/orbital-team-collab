#!/usr/bin/env python3
"""Source-tree entry point for the offline demo."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from orbital_team.demo_orchestration import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
