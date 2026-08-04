from __future__ import annotations

import subprocess
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[3]
    subprocess.Popen(['py', str(root / 'main_ui.py')], cwd=str(root))


if __name__ == '__main__':
    main()
