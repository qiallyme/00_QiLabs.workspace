"""
Compatibility wrapper for core_qi_codex.
Canonical implementation is located in tools/qi_codex/qi_codex.py
"""

from tools.qi_codex.qi_codex import *  # noqa: F401, F403
from tools.qi_codex.qi_codex import main

if __name__ == "__main__":
    main()
