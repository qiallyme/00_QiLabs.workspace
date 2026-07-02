from __future__ import annotations

import json
import shutil
from pathlib import Path
from core.plan import file_sha256, write_json
from core.context import iso_now

STEP_NAME = "Undo last applied run"


def _load_latest_manifest(ctx) -> tuple[Path | None, dict | None]:
    explicit = ctx.state.get("undo_manifest_file")
    if explicit:
        p = Path(explicit)
    else:
        pointer = ctx.manifests_dir / "latest_apply_manifest.json"
        if not pointer.exists():
            ctx.warn("No latest apply manifest pointer found. Nothing to undo.")
            return None, None
        data = json.loads(pointer.read_text(encoding="utf-8"))
        p = Path(data.get("latest_apply_manifest", ""))
    if not p.exists():
        ctx.error(f"Apply manifest does not exist: {p}")
        return p, None
    return p, json.loads(p.read_text(encoding="utf-8"))


def _resolve_backup(ctx, backup_file: str | None) -> Path | None:
    if not backup_file:
        return None
    p = Path(backup_file)
    if not p.is_absolute():
        p = ctx.root / p
    return p


def _undo_write_restore(ctx, action: dict) -> tuple[bool, str]:
    undo = action.get("undo", {})
    target = Path(undo.get("target") or action.get("path"))
    expected_current = undo.get("verify_current_sha256")
    actual_current = file_sha256(target)

    if actual_current != expected_current:
        return False, f"current hash mismatch for restore: {target} expected={expected_current} actual={actual_current}"

    backup = _resolve_backup(ctx, undo.get("backup_file") or action.get("backup_file"))
    if not backup or not backup.exists():
        return False, f"backup missing for restore: {target} backup={backup}"

    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(backup, target)
    restored_hash = file_sha256(target)
    expected_restore = undo.get("restore_sha256")
    if restored_hash != expected_restore:
        return False, f"restore hash mismatch: {target} expected={expected_restore} actual={restored_hash}"
    ctx.mark_changed(target)
    return True, f"restored file from backup: {target}"


def _undo_write_delete_created(ctx, action: dict) -> tuple[bool, str]:
    undo = action.get("undo", {})
    target = Path(undo.get("target") or action.get("path"))
    expected_current = undo.get("verify_current_sha256")
    actual_current = file_sha256(target)

    if not target.exists():
        return False, f"created file already missing: {target}"
    if actual_current != expected_current:
        return False, f"created file changed since apply, skip delete: {target} expected={expected_current} actual={actual_current}"
    target.unlink()
    ctx.mark_changed(target)
    return True, f"deleted file created by apply run: {target}"


def _undo_rename_back(ctx, action: dict) -> tuple[bool, str]:
    undo = action.get("undo", {})
    old = Path(undo.get("old_path") or action.get("old_path"))
    new = Path(undo.get("new_path") or action.get("new_path"))
    expected_current = undo.get("verify_current_sha256")
    actual_current = file_sha256(new)

    if not new.exists():
        return False, f"renamed target missing, cannot rename back: {new}"
    if old.exists():
        return False, f"original path already exists, skip rename back: {old}"
    if actual_current != expected_current:
        return False, f"renamed file changed since apply, skip rename back: {new} expected={expected_current} actual={actual_current}"

    old.parent.mkdir(parents=True, exist_ok=True)
    new.rename(old)
    ctx.mark_changed(old)
    return True, f"renamed back: {new} -> {old}"


def _undo_action(ctx, action: dict) -> tuple[bool, str]:
    undo = action.get("undo") or {}
    kind = undo.get("action")
    if action.get("status") != "applied":
        return False, f"action was not applied, skip: index={action.get('index')} status={action.get('status')}"
    if kind == "restore_backup":
        return _undo_write_restore(ctx, action)
    if kind == "delete_created_file":
        return _undo_write_delete_created(ctx, action)
    if kind == "rename_back":
        return _undo_rename_back(ctx, action)
    return False, f"unknown undo action: {kind}"


def run(ctx):
    if ctx.dry_run:
        ctx.warn("Undo was called in dry-run mode. Use the Undo Last Applied Run button to actually restore files.")
        ctx.add_result(STEP_NAME, {"status": "skipped dry-run"})
        return

    manifest_path, manifest = _load_latest_manifest(ctx)
    if not manifest:
        ctx.add_result(STEP_NAME, {"status": "no manifest", "undone": 0, "skipped": 0})
        return

    actions = list(manifest.get("actions", []))
    undone = 0
    skipped = 0
    undo_records = []

    # Reverse order matters: undo renames/content edits in the opposite order of apply.
    for action in reversed(actions):
        ok, message = _undo_action(ctx, action)
        record = {
            "source_action_index": action.get("index"),
            "source_action_type": action.get("type"),
            "status": "undone" if ok else "skipped",
            "message": message,
        }
        undo_records.append(record)
        if ok:
            undone += 1
            ctx.info(message)
        else:
            skipped += 1
            ctx.warn(message)

    undo_manifest = {
        "schema_version": "1.0",
        "tool": ctx.config.get("tool_name", "QiLabs Housekeeping Console"),
        "tool_version": ctx.config.get("version", "unknown"),
        "manifest_type": "undo_run",
        "undo_run_id": ctx.run_id,
        "created_at": iso_now(),
        "source_apply_manifest": str(manifest_path),
        "source_apply_run_id": manifest.get("apply_run_id"),
        "summary": {
            "source_actions": len(actions),
            "undone": undone,
            "skipped": skipped,
            "warnings": len(ctx.state.get("warnings", [])),
            "errors": len(ctx.state.get("errors", [])),
            "note": "Skipped undo actions are intentional safety stops when files moved or changed after apply.",
        },
        "actions": undo_records,
        "warnings": ctx.state.get("warnings", []),
        "errors": ctx.state.get("errors", []),
        "report_file": str(ctx.report_file),
        "log_file": str(ctx.log_file),
    }
    out = ctx.manifests_dir / f"undo-manifest-{ctx.run_id}.json"
    write_json(out, undo_manifest)
    ctx.state["undo_manifest_file"] = str(out)

    # Mark source apply manifest as having an undo attempt. This is advisory only.
    try:
        manifest["last_undo_run_id"] = ctx.run_id
        manifest["last_undo_manifest"] = str(out)
        manifest["last_undo_at"] = iso_now()
        Path(manifest_path).write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as exc:
        ctx.warn(f"Could not mark source apply manifest as undone: {exc}")

    ctx.add_result(STEP_NAME, {
        "source_apply_manifest": str(manifest_path),
        "undo_manifest_file": str(out),
        "source_actions": len(actions),
        "undone": undone,
        "skipped": skipped,
    })
