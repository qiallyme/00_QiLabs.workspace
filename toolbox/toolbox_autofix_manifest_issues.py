from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from toolbox_core.plugin_autofix import autofix_all
from toolbox_core.plugin_registry import save_registry


def main() -> None:
    parser = argparse.ArgumentParser(description="Auto-fix safe QiLabs Toolbox plugin manifest issues.")
    parser.add_argument("--apply", action="store_true", help="Actually write changes. Without this, preview only.")
    args = parser.parse_args()

    report = autofix_all(ROOT, apply=args.apply)
    print(json.dumps(report, indent=2))

    if args.apply:
        registry_path = save_registry(ROOT)
        print("")
        print(f"Registry: {registry_path}")
        print(f"Validation: {ROOT / 'toolbox_validation_report.md'}")
    else:
        print("")
        print("Preview only. Run with --apply to fix safe manifest issues.")


if __name__ == "__main__":
    main()
