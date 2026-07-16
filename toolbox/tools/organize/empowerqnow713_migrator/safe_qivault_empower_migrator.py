#!/usr/bin/env python3
"""
safe_qivault_empower_migrator.py

Safe publishing-first reorganizer for:
    C:\QiLabs\40_QiVault\30_empowerqnow713

Defaults:
- dry-run only
- copy mode, not move mode
- never overwrites existing files
- skips hidden/system folders
- logs every planned/applied action

Run dry-run:
    python .\safe_qivault_empower_migrator.py --root "C:\QiLabs\40_QiVault\30_empowerqnow713" --dry-run

Run safe copy:
    python .\safe_qivault_empower_migrator.py --root "C:\QiLabs\40_QiVault\30_empowerqnow713" --apply --mode copy

Run move only after reviewing copy result:
    python .\safe_qivault_empower_migrator.py --root "C:\QiLabs\40_QiVault\30_empowerqnow713" --apply --mode move
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

DEFAULT_MASTER_TEMPLATE = """---
layout: page
title: "{{title}}"
slug: "{{title}}"
summary: ""
status: active
visibility: internal
publish_target: none
publish_url: /{{title}}
created_at: "{{date}} {{time}}"
updated_at: "{{date}} {{time}}"
author: Cody J. Rice-Velasquez
owner: Cody
nav_title: "{{title}}"
nav_group: ""
nav_order: 999
nav_hidden: false
is_index: false
parent_ref: ""
sensitivity: internal
classification:
  - blog-post
realm_label:
  - empowerqnow
tags:
  - EmpowerQNow
keywords: []
aliases: []
context: ""
uid: ""
canonical_ref: ""
source_type: manual
template_key: master-template
---

# {{title}}

## Overview

## Key Information

## Notes / Actions
"""

CANONICAL_DIRS = [
    "00_system/style",
    "00_system/templates",
    "00_system/routing_maps",
    "00_system/prompt_packs",
    "00_system/posting_checklists",
    "00_system/technical_specs",
    "00_system/publishing_platforms",

    "10_publish_queue/00_ready_to_post",
    "10_publish_queue/10_needs_final_edit",
    "10_publish_queue/20_needs_media",
    "10_publish_queue/30_scheduled",
    "10_publish_queue/40_posted",
    "10_publish_queue/90_hold",

    "20_series/00_empowerqnow_core",
    "20_series/00_empowerqnow_core/affirmations",
    "20_series/00_empowerqnow_core/systems",
    "20_series/10_mirrors",
    "20_series/20_the_onion_effect",
    "20_series/30_field_notes",
    "20_series/40_reflections_of_one",
    "20_series/50_tarot_signals",
    "20_series/60_power_studies",
    "20_series/70_the_invisible_care_bill",
    "20_series/80_wonder_project",
    "20_series/80_wonder_project/10_fragments",
    "20_series/80_wonder_project/20_posts",
    "20_series/80_wonder_project/30_longform",
    "20_series/80_wonder_project/40_media_prompts",
    "20_series/80_wonder_project/media",
    "20_series/90_source_work_public",

    "30_books",

    "40_source_private/00_life_material",
    "40_source_private/10_clinical_context",
    "40_source_private/20_family_systems",
    "40_source_private/30_relationship_case_notes",
    "40_source_private/40_legal_financial_evidence",
    "40_source_private/50_tarot_raw",
    "40_source_private/90_locked_do_not_publish",

    "50_media_library/images",
    "50_media_library/video",
    "50_media_library/audio",
    "50_media_library/grok_exports",
    "50_media_library/hero_assets",
    "50_media_library/unused_media",

    "90_archive/duplicate_exports",
    "90_archive/old_indexes",
    "90_archive/messy_imports",
    "90_archive/replaced_versions",
    "90_archive/review_before_move",
]

CANONICAL_ROOTS = {
    "00_system", "10_publish_queue", "20_series", "30_books",
    "40_source_private", "50_media_library", "90_archive"
}

SERIES_MAP = {
    "EmpowerQNow": "00_empowerqnow_core",
    "Field Notes": "30_field_notes",
    "Mirrors": "10_mirrors",
    "Power Studies": "60_power_studies",
    "Reflections of One": "40_reflections_of_one",
    "Source Work": "90_source_work_public",
    "Systems": "00_empowerqnow_core/systems",
    "Tarot Signals": "50_tarot_signals",
    "The Invisible Care Bill": "70_the_invisible_care_bill",
    "The Onion Effect": "20_the_onion_effect",
}

ROOT_NAV_KEEP = {"README.md", "_index.md", "_public.md", "index.md", "30_empowerqnow713.md"}

MEDIA_EXT = {".jpg",".jpeg",".png",".gif",".webp",".svg",".mp4",".mov",".m4a",".mp3",".wav",".webm"}
IMAGE_EXT = {".jpg",".jpeg",".png",".gif",".webp",".svg"}
VIDEO_EXT = {".mp4",".mov",".webm"}
AUDIO_EXT = {".m4a",".mp3",".wav"}

PRIVATE_PATTERNS = [
    "joel", "luis", "narcissistic", "relationship analysis", "mental health", "clinical",
    "trauma", "ptsd", "depression", "anxiety", "adhd", "medication", "chlamydia", "descovy",
    "prep", "psychological", "evidence", "fcfeu", "fcfcu", "fcra", "litigation", "gaslighting",
    "family", "caregiver", "medical", "legal", "financial", "estate", "credit", "harm"
]

SYSTEM_PATTERNS = {
    "prompt_packs": ["prompt_pack", "prompt pack", "hero_video_prompt"],
    "routing_maps": ["routing_map", "routing map", "series roadmap", "roadmap"],
    "technical_specs": ["technical_spec", "technical spec"],
    "style": ["style_guide", "style guide", "visual_style"],
    "templates": ["template"],
    "publishing_platforms": ["qsaysit.com", "qsaysit com", "qially_com_blog"],
}


@dataclass
class PlanRow:
    source: Path
    action: str
    destination: Path | None
    reason: str
    final_destination: Path | None = None
    status: str = "planned"


def now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def normalized_rel(path: Path) -> str:
    return path.as_posix().strip("/")


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s.-]+", "", text, flags=re.UNICODE)
    text = re.sub(r"[\s_]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("._- ")
    return text or "untitled"


def unique_path(dst: Path) -> Path:
    """Return dst if free; otherwise return a suffixed non-existing path."""
    if not dst.exists():
        return dst

    stamp = now_stamp()
    stem = dst.stem
    suffix = dst.suffix
    parent = dst.parent

    for i in range(1, 10000):
        candidate = parent / f"{stem}__migrated_{stamp}_{i:03d}{suffix}"
        if not candidate.exists():
            return candidate

    raise RuntimeError(f"Could not find safe unique name for {dst}")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def classify(rel: Path) -> tuple[str, Path | None, str]:
    """Classify a relative path under the project root."""
    rel_s = normalized_rel(rel)
    parts = rel.parts
    name = rel.name
    lower = rel_s.lower()
    name_lower = name.lower()
    ext = rel.suffix.lower()

    if not parts:
        return "skip", None, "empty path"

    if parts[0] in CANONICAL_ROOTS:
        return "skip", rel, "already in canonical structure"

    if parts[0].startswith("."):
        return "skip", None, "hidden/system vault folder out of scope"

    if len(parts) == 1 and name in ROOT_NAV_KEEP:
        return "keep", rel, "root navigation/public index; review manually later"

    if name_lower in {"_index.md", "index.md", "20_posts.md", "30_books.md"} and len(parts) <= 2:
        return "move", Path("90_archive/old_indexes") / name, "generic old index/root index candidate"

    if parts[0] == "00_Style":
        rest = Path(*parts[1:]) if len(parts) > 1 else Path(name)
        return "move", Path("00_system/style") / rest, "style folder"

    for folder, patterns in SYSTEM_PATTERNS.items():
        if any(p in lower for p in patterns):
            return "move", Path("00_system") / folder / name, f"system file: {folder}"

    if parts[0] == "30_Books":
        rest = Path(*parts[1:]) if len(parts) > 1 else Path(name)
        return "move", Path("30_books") / rest, "book/manuscript tree"

    if parts[0] == "20_Posts":
        if len(parts) >= 2 and parts[1] in SERIES_MAP:
            mapped = SERIES_MAP[parts[1]]
            rest = Path(*parts[2:]) if len(parts) > 2 else Path()
            return "move", Path("20_series") / mapped / rest, f"public series: {parts[1]}"
        if len(parts) == 2:
            return "move", Path("20_series/00_empowerqnow_core") / name, "loose public post under 20_Posts"
        return "move", Path("90_archive/messy_imports") / rel, "unmapped 20_Posts item"

    if ext in MEDIA_EXT:
        if "grok" in name_lower:
            return "move", Path("50_media_library/grok_exports") / name, "Grok media/export"
        if ext in IMAGE_EXT:
            return "move", Path("50_media_library/images") / name, "loose image"
        if ext in VIDEO_EXT:
            return "move", Path("50_media_library/video") / name, "loose video"
        if ext in AUDIO_EXT:
            return "move", Path("50_media_library/audio") / name, "loose audio"
        return "move", Path("50_media_library/unused_media") / name, "loose media"

    if any(p in lower for p in PRIVATE_PATTERNS):
        if any(p in lower for p in ["fcfeu", "fcfcu", "fcra", "litigation", "legal", "financial", "estate", "credit"]):
            return "move", Path("40_source_private/40_legal_financial_evidence") / name, "private legal/financial/evidence material"
        if any(p in lower for p in ["joel", "luis", "relationship", "narcissistic"]):
            return "move", Path("40_source_private/30_relationship_case_notes") / name, "private relationship/case material"
        if any(p in lower for p in ["mental", "clinical", "trauma", "ptsd", "adhd", "anxiety", "depression", "medication", "psychological", "medical"]):
            return "move", Path("40_source_private/10_clinical_context") / name, "private clinical/health context"
        return "move", Path("40_source_private/00_life_material") / name, "private source material"

    if any(p in lower for p in ["empowerqnow", "living code", "living qidex", "sacred teachings", "manifesto", "themes"]):
        return "move", Path("20_series/00_empowerqnow_core") / name, "EmpowerQNow core public/doctrine"

    if "affirmation" in lower or "survivor" in lower:
        return "move", Path("20_series/00_empowerqnow_core/affirmations") / name, "public affirmations/survivor writing"

    if "untitled" in name_lower or "gemini-code" in name_lower:
        return "move", Path("90_archive/messy_imports") / name, "messy/generated import"

    return "review", Path("90_archive/review_before_move") / name, "unclassified; review before moving"


def build_plan(root: Path) -> list[PlanRow]:
    rows: list[PlanRow] = []
    for src in root.rglob("*"):
        if not src.is_file():
            continue
        rel = src.relative_to(root)
        action, dest_rel, reason = classify(rel)

        dest = None
        if dest_rel is not None:
            dest = root / dest_rel

        rows.append(PlanRow(
            source=src,
            action=action,
            destination=dest,
            reason=reason
        ))
    return rows


def render_index(template: str, title: str, nav_group: str = "", parent_ref: str = "") -> str:
    now = datetime.now()
    date = now.strftime("%Y-%m-%d")
    time = now.strftime("%H:%M:%S")
    replacements = {
        "{{title}}": title,
        "{{date}}": date,
        "{{time}}": time,
    }
    out = template
    for k, v in replacements.items():
        out = out.replace(k, v)

    # Light targeted replacements without trying to be a full YAML parser.
    out = re.sub(r'nav_group: ""', f'nav_group: "{nav_group}"', out)
    out = re.sub(r'parent_ref: ""', f'parent_ref: "{parent_ref}"', out)
    out = re.sub(r'is_index: false', 'is_index: true', out)
    return out


def create_dirs_and_indexes(root: Path, template: str, apply: bool, make_indexes: bool) -> list[dict]:
    log: list[dict] = []
    for rel_s in CANONICAL_DIRS:
        d = root / rel_s
        if apply:
            d.mkdir(parents=True, exist_ok=True)
        log.append({"action": "mkdir", "path": str(d), "status": "applied" if apply else "dry-run"})

        if not make_indexes:
            continue

        index_path = d / "_index.md"
        title = Path(rel_s).name.replace("_", " ").title()
        if index_path.exists():
            log.append({"action": "index", "path": str(index_path), "status": "skipped_exists"})
            continue

        if apply:
            index_path.write_text(render_index(template, title), encoding="utf-8")
            status = "created"
        else:
            status = "would_create"

        log.append({"action": "index", "path": str(index_path), "status": status})

    return log


def apply_plan(rows: list[PlanRow], root: Path, mode: str, apply: bool) -> list[PlanRow]:
    for row in rows:
        if row.action in {"skip", "keep"}:
            row.status = row.action
            row.final_destination = row.destination
            continue

        if row.action not in {"move", "review"}:
            row.status = f"unknown_action_{row.action}"
            continue

        if row.destination is None:
            row.status = "no_destination"
            continue

        if not row.source.exists():
            row.status = "source_missing"
            continue

        final = unique_path(row.destination)
        row.final_destination = final

        if row.action == "review":
            # Review rows are copied/moved to review bucket, not silently skipped.
            pass

        if not apply:
            row.status = "dry-run"
            continue

        final.parent.mkdir(parents=True, exist_ok=True)

        if mode == "copy":
            shutil.copy2(row.source, final)
            row.status = "copied"
        elif mode == "move":
            shutil.move(str(row.source), str(final))
            row.status = "moved"
        else:
            raise ValueError(f"Invalid mode: {mode}")

    return rows


def write_logs(root: Path, rows: list[PlanRow], dir_log: list[dict], apply: bool) -> None:
    log_dir = root / "00_system" / "migration_logs"
    if apply:
        log_dir.mkdir(parents=True, exist_ok=True)

    stamp = now_stamp()
    csv_path = log_dir / f"migration_log_{stamp}.csv"
    md_path = log_dir / f"MIGRATION_LOG_{stamp}.md"
    inventory_path = log_dir / f"CONTENT_INVENTORY_{stamp}.md"
    collision_path = log_dir / f"COLLISIONS_REVIEW_{stamp}.md"

    rows_as_dict = []
    collisions = []
    for row in rows:
        src_rel = row.source.relative_to(root).as_posix() if row.source.is_relative_to(root) else str(row.source)
        dest_rel = ""
        final_rel = ""
        if row.destination:
            dest_rel = row.destination.relative_to(root).as_posix() if row.destination.is_relative_to(root) else str(row.destination)
        if row.final_destination:
            final_rel = row.final_destination.relative_to(root).as_posix() if row.final_destination.is_relative_to(root) else str(row.final_destination)

        collision = bool(dest_rel and final_rel and dest_rel != final_rel)
        if collision:
            collisions.append(row)

        rows_as_dict.append({
            "source": src_rel,
            "action": row.action,
            "planned_destination": dest_rel,
            "final_destination": final_rel,
            "reason": row.reason,
            "status": row.status,
            "collision_renamed": collision,
        })

    if apply:
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows_as_dict[0].keys()) if rows_as_dict else ["source"])
            writer.writeheader()
            writer.writerows(rows_as_dict)

        counts = {}
        for r in rows_as_dict:
            counts[r["status"]] = counts.get(r["status"], 0) + 1

        md_lines = [
            f"# Migration Log — {stamp}",
            "",
            f"- Root: `{root}`",
            f"- Mode applied: `{apply}`",
            "",
            "## Counts",
            "",
        ]
        for k, v in sorted(counts.items()):
            md_lines.append(f"- {k}: {v}")

        md_lines.extend(["", "## Directory/index actions", ""])
        for entry in dir_log:
            md_lines.append(f"- {entry['action']}: `{entry['path']}` — {entry['status']}")

        md_lines.extend(["", "## File actions", ""])
        for r in rows_as_dict:
            md_lines.append(
                f"- **{r['status']}** `{r['source']}` → `{r['final_destination']}`  \n"
                f"  Reason: {r['reason']}"
            )
        md_path.write_text("\n".join(md_lines), encoding="utf-8")

        inv_lines = [
            f"# Content Inventory — {stamp}",
            "",
            "| Status | Action | Source | Destination | Reason |",
            "|---|---|---|---|---|",
        ]
        for r in rows_as_dict:
            inv_lines.append(f"| {r['status']} | {r['action']} | `{r['source']}` | `{r['final_destination']}` | {r['reason']} |")
        inventory_path.write_text("\n".join(inv_lines), encoding="utf-8")

        col_lines = [f"# Collisions Review — {stamp}", ""]
        if not collisions:
            col_lines.append("No destination collisions required renamed output files.")
        else:
            for row in collisions:
                col_lines.append(f"- `{row.destination}` renamed safely to `{row.final_destination}`")
        collision_path.write_text("\n".join(col_lines), encoding="utf-8")
    else:
        print("\n--- DRY RUN SUMMARY ---")
        counts = {}
        for row in rows:
            counts[row.status] = counts.get(row.status, 0) + 1
        for k, v in sorted(counts.items()):
            print(f"{k}: {v}")
        print("\nNo files changed. Re-run with --apply when ready.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Safely reorganize EmpowerQNow713 writing section.")
    parser.add_argument("--root", required=True, help=r'Target root, e.g. C:\QiLabs\40_QiVault\30_empowerqnow713')
    parser.add_argument("--mode", choices=["copy", "move"], default="copy", help="Default: copy. Use move only after verifying.")
    parser.add_argument("--apply", action="store_true", help="Actually create/copy/move files. Without this, dry-run only.")
    parser.add_argument("--dry-run", action="store_true", help="Explicit dry-run. This is default unless --apply is provided.")
    parser.add_argument("--template", default="", help="Optional path to master_template.md. Uses embedded template if omitted.")
    parser.add_argument("--no-indexes", action="store_true", help="Do not create _index.md files in canonical folders.")
    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        print(f"ERROR: root does not exist or is not a folder: {root}")
        return 2

    if root.name.lower() != "30_empowerqnow713":
        print("SAFETY STOP: This script is scoped to a folder named 30_empowerqnow713.")
        print(f"You gave: {root}")
        return 3

    apply = bool(args.apply)
    if args.dry_run:
        apply = False

    template = DEFAULT_MASTER_TEMPLATE
    if args.template:
        template_path = Path(args.template).expanduser().resolve()
        if not template_path.exists():
            print(f"ERROR: template file not found: {template_path}")
            return 4
        template = template_path.read_text(encoding="utf-8", errors="replace")

    print(f"Root: {root}")
    print(f"Mode: {args.mode}")
    print(f"Apply: {apply}")

    rows = build_plan(root)
    dir_log = create_dirs_and_indexes(root, template, apply=apply, make_indexes=not args.no_indexes)
    rows = apply_plan(rows, root=root, mode=args.mode, apply=apply)

    if not apply:
        # Print a short preview.
        preview = rows[:30]
        print("\n--- FIRST 30 PLANNED FILE ACTIONS ---")
        for row in preview:
            src = row.source.relative_to(root)
            dest = row.final_destination.relative_to(root) if row.final_destination and row.final_destination.is_relative_to(root) else row.final_destination
            print(f"{row.status.upper():8} | {row.action:6} | {src} -> {dest} | {row.reason}")
        if len(rows) > len(preview):
            print(f"... {len(rows) - len(preview)} more rows not shown.")

    write_logs(root, rows, dir_log, apply=apply)

    if apply:
        print("Done. Logs written under: 00_system/migration_logs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
