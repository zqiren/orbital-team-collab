#!/usr/bin/env python3
from __future__ import annotations

import sys

from orbital_team.member_adapter import main


if __name__ == "__main__":
    raise SystemExit(main(["session-start", "--provider", "claude-code", *sys.argv[1:]]))
