import json
from pathlib import Path
import datetime

STEP_NAME = "Generate QiCode audit report"

def run(ctx):
    reports_dir = Path(__file__).parent.parent / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    report_file = reports_dir / f"qicode_audit_report_{timestamp}.md"
    
    lines = [
        "# QiCode Maintenance Audit Report",
        f"**Run ID**: `{ctx.run_id}`",
        f"**Timestamp**: {datetime.datetime.now().astimezone().isoformat()}",
        f"**Mode**: {'PREVIEW / PLAN ONLY (Dry Run)' if ctx.dry_run else 'APPLIED'}",
        ""
    ]
    
    for step_name, data in ctx.results.items():
        if step_name == STEP_NAME: continue
        
        lines.append(f"## {step_name}")
        lines.append("```json")
        lines.append(json.dumps(data, indent=2))
        lines.append("```")
        lines.append("")
        
    report_text = "\n".join(lines)
    report_file.write_text(report_text, encoding="utf-8")
    
    ctx.add_result(STEP_NAME, {
        "report_generated": str(report_file)
    })
    ctx.info(f"QiCode Audit Report generated at: {report_file}")
