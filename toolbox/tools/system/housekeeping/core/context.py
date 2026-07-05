from __future__ import annotations

import datetime as _dt
import json
import os
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Any
from core.plan import file_sha256, sha256_bytes, safe_payload_name, write_json


def now_stamp() -> str:
    return _dt.datetime.now().strftime("%Y%m%d-%H%M%S")


def iso_now() -> str:
    return _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@dataclass
class RunContext:
    config_path: Path
    dry_run: bool = True
    allow_renames: bool = False
    push: bool = False
    screen_log: Callable[[str], None] | None = None
    run_id: str = field(default_factory=now_stamp)
    config: dict[str, Any] = field(default_factory=dict)
    state: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.config_path = Path(self.config_path)
        self.root = self.config_path.parent
        self.config = json.loads(self.config_path.read_text(encoding="utf-8"))
        self.logs_dir = self.root / "logs"
        self.reports_dir = self.root / "reports"
        self.backups_dir = self.root / "backups" / self.run_id
        self.plans_dir = self.root / "plans"
        self.manifests_dir = self.root / "manifests"
        self.summaries_dir = self.root / "summaries"
        self.plan_payloads_dir = self.plans_dir / self.run_id / "payloads"
        self.manifest_payloads_dir = self.manifests_dir / self.run_id / "payloads"
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.backups_dir.mkdir(parents=True, exist_ok=True)
        self.plans_dir.mkdir(parents=True, exist_ok=True)
        self.manifests_dir.mkdir(parents=True, exist_ok=True)
        self.summaries_dir.mkdir(parents=True, exist_ok=True)
        self.plan_payloads_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_payloads_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.logs_dir / f"housekeeping-{self.run_id}.jsonl"
        self.report_file = self.reports_dir / f"housekeeping-report-{self.run_id}.md"
        self.summary_file = self.summaries_dir / f"housekeeping-summary-{self.run_id}.md"
        self.inventory_file = self.reports_dir / f"inventory-{self.run_id}.json"
        self.rename_plan_file = self.reports_dir / f"rename-plan-{self.run_id}.json"
        self.plan_file = self.plans_dir / f"housekeeping-plan-{self.run_id}.json"
        self.state.setdefault("results", [])
        self.state.setdefault("warnings", [])
        self.state.setdefault("errors", [])
        self.state.setdefault("rename_map", {})
        self.state.setdefault("changed_files", [])
        self.state.setdefault("planned_actions", [])
        self.state.setdefault("apply_manifest_actions", [])
        self.state.setdefault("run_summary", {})


    def plan_write_text(self, file_path: Path, new_text: str, step: str, description: str = "") -> None:
        """Record an exact write operation during dry-run so Apply can use the saved plan without rescanning."""
        file_path = Path(file_path)
        payload_bytes = new_text.encode("utf-8")
        before_hash = file_sha256(file_path)
        after_hash = sha256_bytes(payload_bytes)
        idx = len(self.state.get("planned_actions", [])) + 1
        payload_name = safe_payload_name(file_path, after_hash, idx)
        payload_path = self.plan_payloads_dir / payload_name
        payload_path.parent.mkdir(parents=True, exist_ok=True)
        payload_path.write_bytes(payload_bytes)
        action = {
            "type": "write_text",
            "step": step,
            "path": str(file_path),
            "before_sha256": before_hash,
            "after_sha256": after_hash,
            "payload_file": str(payload_path.relative_to(self.root)),
            "description": description or f"Write {file_path}",
        }
        self.state.setdefault("planned_actions", []).append(action)

    def plan_rename(self, old_path: Path, new_path: Path, step: str, description: str = "") -> None:
        """Record an exact rename operation during dry-run so Apply can use the saved plan without rescanning."""
        old_path = Path(old_path)
        new_path = Path(new_path)
        action = {
            "type": "rename",
            "step": step,
            "old_path": str(old_path),
            "new_path": str(new_path),
            "old_sha256": file_sha256(old_path),
            "description": description or f"Rename {old_path} -> {new_path}",
        }
        self.state.setdefault("planned_actions", []).append(action)

    def save_plan(self, modules: list[str] | None = None, plan_kind: str = "manual") -> Path:
        data = {
            "schema_version": "1.0",
            "tool": self.config.get("tool_name", "QiLabs Housekeeping Console"),
            "run_id": self.run_id,
            "created_at": iso_now(),
            "mode": "dry-run-plan",
            "plan_kind": plan_kind,
            "modules": modules or [],
            "allow_renames": self.allow_renames,
            "push_requested": self.push,
            "action_count": len(self.state.get("planned_actions", [])),
            "actions": self.state.get("planned_actions", []),
            "warnings": self.state.get("warnings", []),
            "errors": self.state.get("errors", []),
            "results": self.state.get("results", []),
            "report_file": str(self.report_file),
            "log_file": str(self.log_file),
        }
        write_json(self.plan_file, data)
        self.info(f"Saved approval plan: {self.plan_file}")
        return self.plan_file

    def path(self, key: str) -> Path:
        return Path(self.config[key])

    def log(self, level: str, message: str, **extra: Any) -> None:
        event = {
            "ts": iso_now(),
            "run_id": self.run_id,
            "level": level.upper(),
            "message": message,
            **extra,
        }
        with self.log_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
        if self.screen_log:
            self.screen_log(f"[{event['level']}] {message}")

    def info(self, message: str, **extra: Any) -> None:
        self.log("info", message, **extra)

    def warn(self, message: str, **extra: Any) -> None:
        self.state["warnings"].append(message)
        self.log("warn", message, **extra)

    def error(self, message: str, **extra: Any) -> None:
        self.state["errors"].append(message)
        self.log("error", message, **extra)

    def add_result(self, step: str, summary: dict[str, Any]) -> None:
        self.state["results"].append({"step": step, **summary})
        self.info(f"{step}: {summary}")

    def backup_file(self, file_path: Path) -> Path | None:
        file_path = Path(file_path)
        if not file_path.exists() or self.dry_run:
            return None
        try:
            root = Path(self.config["qilabs_root"])
            rel = file_path.resolve().relative_to(root.resolve())
        except Exception:
            rel = Path(file_path.name)
        dest = self.backups_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(file_path.read_bytes())
        return dest

    def mark_changed(self, file_path: Path) -> None:
        self.state["changed_files"].append(str(file_path))
