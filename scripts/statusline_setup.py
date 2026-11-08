"""Add or remove Viaduct's progress status line (called by session-start.sh).

    python3 statusline_setup.py install     # never replaces a status line the user already has
    python3 statusline_setup.py uninstall   # only removes Viaduct's own
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from kipcb import progress  # noqa: E402

if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else ""
    if action == "install":
        progress.install_statusline()
    elif action == "uninstall":
        progress.uninstall_statusline()
    else:
        sys.exit("usage: statusline_setup.py install|uninstall")
