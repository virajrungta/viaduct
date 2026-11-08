"""Print Viaduct's design progress line for Claude Code's status bar (run by statusline.sh)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from kipcb import progress  # noqa: E402

if __name__ == "__main__":
    print(progress.statusline())
