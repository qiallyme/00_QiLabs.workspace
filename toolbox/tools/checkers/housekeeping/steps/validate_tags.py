from pathlib import Path
import json
import re
from collections import Counter
from core.fs import iter_files, is_protected
from core.frontmatter import split_frontmatter, parse_frontmatter_keys

STEP_NAME = "Validate global tags"

TAG_RE_STRICT = re.compile(r"^#[a-z0-9][a-z0-9/_-]*$")
PROJECT_SPECIFIC_ALWAYS = {"#care-record", "#lisa-care-record"}


def parse_inline_tags(value: str) -> list[str]:
    value = value.strip()
    if value in ("", "[]"):
        return []
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [x.strip().strip('"').strip("'") for x in inner.split(",") if x.strip()]
    return [value.strip('"').strip("'")]


def run(ctx):
    tags_path = Path(ctx.config["tags_file"])
    if not tags_path.exists():
        ctx.warn(f"Tags file missing: {tags_path}")
        ctx.add_result(STEP_NAME, {"status": "missing"})
        return

    try:
        data = json.loads(tags_path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        ctx.error(f"Tags file is not valid JSON: {tags_path} -> {exc}")
        ctx.add_result(STEP_NAME, {"status": "invalid_json", "path": str(tags_path), "error": str(exc)})
        return

    allowed = []
    for category, values in data.get("allowed_tags", {}).items():
        for tag in values:
            allowed.append((category, tag))

    flat = [t for _cat, t in allowed]
    allowed_set = set(flat)
    dupes = sorted([t for t, c in Counter(flat).items() if c > 1])
    invalid = []
    uppercase_exhibit = []

    allow_upper_exhibits = ctx.config.get("tags", {}).get("style_exceptions", {}).get("allow_uppercase_exhibit_letters", True)

    for category, tag in allowed:
        if not TAG_RE_STRICT.match(tag):
            if allow_upper_exhibits and tag.startswith("#exhibit/") and re.match(r"^#exhibit/[A-Z]-[a-z0-9-]+$", tag):
                uppercase_exhibit.append(tag)
            else:
                invalid.append(tag)

    always = data.get("tag_policy", {}).get("always_include", [])
    missing_always = [t for t in always if t not in flat]
    project_specific_always = [t for t in always if t in PROJECT_SPECIFIC_ALWAYS]

    if dupes:
        ctx.warn(f"Duplicate tags found: {dupes}")
    if invalid:
        ctx.warn(f"Tags violating policy: {invalid[:20]}")
    if uppercase_exhibit:
        ctx.warn("Uppercase exhibit tags found but allowed by configured exception. Do not silently rewrite them.")
    if missing_always:
        ctx.warn(f"always_include tags missing from allowed_tags: {missing_always}")
    if project_specific_always and ctx.config.get("tags", {}).get("global_enforcement"):
        ctx.warn(
            "Global tag registry contains project-specific always_include tags. Treat these as profile defaults, not tags to add to every note: "
            + ", ".join(project_specific_always)
        )

    unknown_tags = Counter()
    scanned_md = 0
    if ctx.config.get("tags", {}).get("global_enforcement"):
        roots = [Path(p) for p in ctx.config.get("tags", {}).get("scan_scope_roots", ctx.config.get("default_scope_roots", []))]
        for p in iter_files(roots, ctx.config, suffixes={".md"}):
            scanned_md += 1
            text = p.read_text(encoding="utf-8-sig", errors="replace")
            fm, _body = split_frontmatter(text)
            keys = parse_frontmatter_keys(fm)
            for tag in parse_inline_tags(keys.get("tags", "[]")):
                if tag and tag not in allowed_set:
                    unknown_tags[tag] += 1

    if unknown_tags:
        ctx.warn(f"Unknown tags found in markdown frontmatter: {dict(unknown_tags.most_common(25))}")

    ctx.add_result(STEP_NAME, {
        "profile": ctx.config.get("tags", {}).get("profile_name"),
        "global_enforcement": ctx.config.get("tags", {}).get("global_enforcement"),
        "categories": len(data.get("allowed_tags", {})),
        "allowed_tags": len(flat),
        "duplicates": len(dupes),
        "invalid_policy_tags": len(invalid),
        "uppercase_exhibit_exceptions": len(uppercase_exhibit),
        "markdown_files_tag_scanned": scanned_md,
        "unknown_tags": len(unknown_tags),
        "project_specific_always_include": project_specific_always,
    })