from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
from typing import Any


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha256(path: Path) -> str | None:
    path = Path(path)
    if not path.exists() or not path.is_file():
        return None
    return sha256_bytes(path.read_bytes())


def safe_payload_name(path: Path, after_hash: str, index: int) -> str:
    suffix = path.suffix or ".txt"
    return f"{index:05d}_{after_hash[:16]}{suffix}"


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))
