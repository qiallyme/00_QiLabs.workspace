from __future__ import annotations

import json
import shutil
from pathlib import Path
from core.plan import file_sha256, write_json
from core.context import iso_now

STEP_NAME = "Apply saved approval plan"


def _load_plan(ctx) -> dict:
    plan_path = ctx.state.get("approval_plan_file") or ctx.state.get("manual_plan_file") or ctx.state.get("plan_file")
    if not plan_path:
        raise ValueError("No saved plan file was provided to apply.")
    p = Path(plan_path)
    if not p.exists():
        raise FileNotFoundError(f"Saved plan file does not exist: {p}")
    ctx.state["loaded_plan_file"] = str(p)
    return json.loads(p.read_text(encoding="utf-8"))


def _payload_path(ctx, action: dict) -> Path:
    raw = action.get("payload_file")
    if not raw:
        raise ValueError("write_text action has no payload_file")
    p = Path(raw)
    if not p.is_absolute():
        p = ctx.root / p
    return p


def _manifest_backup(ctx, target: Path, action_index: int) -> Path | None:
    """Store the exact pre-apply bytes needed for one-click undo."""
    target = Path(target)
    if not target.exists() or not target.is_file():
        return None
    undo_dir = ctx.manifest_payloads_dir
    undo_dir.mkdir(parents=True, exist_ok=True)
    suffix = target.suffix or ".bin"
    backup = undo_dir / f"{action_index:05d}_before{suffix}"
    shutil.copy2(target, backup)
    return backup


def _rel_to_tool_root(ctx, p: Path | None) -> str | None:
    if not p:
        return None
    try:
        return str(Path(p).resolve().relative_to(ctx.root.resolve()))
    except Exception:
        return str(p)


def _record(ctx, record: dict) -> None:
    ctx.state.setdefault("apply_manifest_actions", []).append(record)


def _apply_write(ctx, action: dict, action_index: int) -> bool:
    target = Path(action["path"])
    expected_before = action.get("before_sha256")
    actual_before = file_sha256(target)

    base_record = {
        "index": action_index,
        "type": "write_text",
        "step": action.get("step"),
        "path": str(target),
        "description": action.get("description", ""),
        "expected_before_sha256": expected_before,
        "actual_before_sha256": actual_before,
        "planned_after_sha256": action.get("after_sha256"),
    }

    if expected_before != actual_before:
        ctx.error(
            f"Skipped write because file changed since preview: {target} "
            f"expected={expected_before} actual={actual_before}"
        )
        _record(ctx, {**base_record, "status": "skipped", "reason": "before_hash_mismatch"})
        return False

    payload = _payload_path(ctx, action)
    if not payload.exists():
        ctx.error(f"Skipped write because payload is missing: {payload}")
        _record(ctx, {**base_record, "status": "skipped", "reason": "missing_payload"})
        return False

    before_existed = target.exists()
    backup = _manifest_backup(ctx, target, action_index)
    new_text = payload.read_text(encoding="utf-8")
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        ctx.backup_file(target)
    target.write_text(new_text, encoding="utf-8")
    after = file_sha256(target)
    if after != action.get("after_sha256"):
        ctx.error(f"Write hash mismatch after applying: {target}")
        _record(ctx, {**base_record, "status": "failed", "reason": "after_hash_mismatch", "actual_after_sha256": after})
        return False

    ctx.mark_changed(target)
    ctx.info(f"Applied planned write: {target}")
    undo_action = "restore_backup" if before_existed else "delete_created_file"
    _record(ctx, {
        **base_record,
        "status": "applied",
        "actual_after_sha256": after,
        "before_existed": before_existed,
        "backup_file": _rel_to_tool_root(ctx, backup),
        "undo": {
            "action": undo_action,
            "target": str(target),
            "backup_file": _rel_to_tool_root(ctx, backup),
            "verify_current_sha256": after,
            "restore_sha256": expected_before,
        },
    })
    return True


def _apply_rename(ctx, action: dict, action_index: int) -> bool:
    old = Path(action["old_path"])
    new = Path(action["new_path"])
    expected = action.get("old_sha256")
    actual = file_sha256(old)

    base_record = {
        "index": action_index,
        "type": "rename",
        "step": action.get("step"),
        "old_path": str(old),
        "new_path": str(new),
        "description": action.get("description", ""),
        "expected_old_sha256": expected,
        "actual_old_sha256": actual,
    }

    if not ctx.allow_renames:
        ctx.warn(f"Skipped planned rename because Include filename renames is unchecked: {old} -> {new}")
        _record(ctx, {**base_record, "status": "skipped", "reason": "renames_disabled"})
        return False
    if not old.exists():
        ctx.error(f"Skipped rename because source is missing: {old}")
        _record(ctx, {**base_record, "status": "skipped", "reason": "source_missing"})
        return False
    if new.exists():
        ctx.error(f"Skipped rename because target already exists: {new}")
        _record(ctx, {**base_record, "status": "skipped", "reason": "target_exists"})
        return False
    if expected != actual:
        ctx.error(
            f"Skipped rename because source changed since preview: {old} "
            f"expected={expected} actual={actual}"
        )
        _record(ctx, {**base_record, "status": "skipped", "reason": "before_hash_mismatch"})
        return False

    backup = _manifest_backup(ctx, old, action_index)
    ctx.backup_file(old)
    new.parent.mkdir(parents=True, exist_ok=True)
    old.rename(new)
    new_hash = file_sha256(new)
    ctx.mark_changed(new)
    ctx.info(f"Applied planned rename: {old} -> {new}")
    _record(ctx, {
        **base_record,
        "status": "applied",
        "new_sha256": new_hash,
        "backup_file": _rel_to_tool_root(ctx, backup),
        "undo": {
            "action": "rename_back",
            "old_path": str(old),
            "new_path": str(new),
            "verify_current_sha256": new_hash,
            "restore_sha256": expected,
        },
    })
    return True


def _write_apply_manifest(ctx, plan: dict, applied: int, failed: int) -> Path:
    manifest_dir = ctx.manifests_dir
    manifest_dir.mkdir(parents=True, exist_ok=True)
    actions = ctx.state.get("apply_manifest_actions", [])
    manifest = {
        "schema_version": "1.0",
        "tool": ctx.config.get("tool_name", "QiLabs Housekeeping Console"),
        "tool_version": ctx.config.get("version", "unknown"),
        "manifest_type": "apply_run",
        "apply_run_id": ctx.run_id,
        "created_at": iso_now(),
        "source_plan_file": ctx.state.get("loaded_plan_file"),
        "source_plan_run_id": plan.get("run_id"),
        "source_plan_kind": plan.get("plan_kind"),
        "allow_renames": ctx.allow_renames,
        "push_requested": ctx.push,
        "summary": {
            "planned_actions": len(plan.get("actions", [])),
            "applied": applied,
            "skipped_or_failed": failed,
            "warnings": len(ctx.state.get("warnings", [])),
            "errors": len(ctx.state.get("errors", [])),
            "undoable_applied_actions": sum(1 for a in actions if a.get("status") == "applied" and a.get("undo")),
            "git_note": "Git commits/pushes are not auto-undone. File changes can be restored into the working tree.",
        },
        "actions": actions,
        "warnings": ctx.state.get("warnings", []),
        "errors": ctx.state.get("errors", []),
        "report_file": str(ctx.report_file),
        "log_file": str(ctx.log_file),
    }
    manifest_file = manifest_dir / f"apply-manifest-{ctx.run_id}.json"
    write_json(manifest_file, manifest)
    write_json(manifest_dir / "latest_apply_manifest.json", {
        "latest_apply_manifest": str(manifest_file),
        "apply_run_id": ctx.run_id,
        "created_at": manifest["created_at"],
        "summary": manifest["summary"],
    })
    ctx.state["apply_manifest_file"] = str(manifest_file)
    ctx.info(f"Saved apply run manifest: {manifest_file}")
    return manifest_file


def run(ctx):
    if ctx.dry_run:
        ctx.warn("Apply saved plan was called in dry-run mode. Nothing was changed.")
        ctx.add_result(STEP_NAME, {"status": "skipped dry-run"})
        return

    plan = _load_plan(ctx)
    actions = plan.get("actions", [])
    if not actions:
        ctx.warn("Saved plan has no file actions to apply.")
        manifest_file = _write_apply_manifest(ctx, plan, 0, 0)
        ctx.add_result(STEP_NAME, {"actions": 0, "applied": 0, "skipped_or_failed": 0, "manifest_file": str(manifest_file)})
        return

    writes = [a for a in actions if a.get("type") == "write_text"]
    renames = [a for a in actions if a.get("type") == "rename"]
    other = [a for a in actions if a.get("type") not in {"write_text", "rename"}]

    applied = 0
    failed = 0
    action_index = 0

    # Writes first, renames second. That preserves planned content edits to old paths before moving them.
    for action in writes:
        action_index += 1
        if _apply_write(ctx, action, action_index):
            applied += 1
        else:
            failed += 1
    for action in renames:
        action_index += 1
        if _apply_rename(ctx, action, action_index):
            applied += 1
        else:
            failed += 1
    for action in other:
        action_index += 1
        ctx.warn(f"Unknown planned action type skipped: {action.get('type')}")
        _record(ctx, {"index": action_index, "type": action.get("type"), "status": "skipped", "reason": "unknown_action_type", "raw": action})
        failed += 1

    manifest_file = _write_apply_manifest(ctx, plan, applied, failed)

    ctx.add_result(STEP_NAME, {
        "plan_file": ctx.state.get("approval_plan_file") or ctx.state.get("manual_plan_file") or ctx.state.get("plan_file"),
        "manifest_file": str(manifest_file),
        "actions": len(actions),
        "write_actions": len(writes),
        "rename_actions": len(renames),
        "applied": applied,
        "skipped_or_failed": failed,
    })
