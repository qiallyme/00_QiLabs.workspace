# QiCode Legacy 50_QiLabs Archive Readiness Audit

- Generated: `2026-07-21T02:17:03`
- QiLabs root: `C:\QiLabs`
- Legacy source compared: `C:\QiLabs\40_QiVault\00_home\00_QiCode\sources\qilabs_legacy_50_qilabs.md`
- QiCode target compared: `C:\QiLabs\40_QiVault\00_home\00_QiCode`
- Coverage threshold: `0.82`

## Decision: SAFE TO ARCHIVE

Expected structure exists and legacy text coverage passed thresholds.

## Detected Paths

### Legacy candidates

- `C:\QiLabs\40_QiVault\00_home\00_QiCode\sources\qilabs_legacy_50_qilabs.md`

### QiCode candidates

- `C:\QiLabs\40_QiVault\00_home\00_QiCode`
- `C:\QiLabs\40_QiVault\40_projects\care_record_lisa\_qiconfig\cleanup_2026-06-29_frontmatter\backups_before_frontmatter\10_qispark\10_QiSpark\00_QiCode`
- `C:\QiLabs\40_QiVault\40_projects\care_record_lisa\_qiconfig\cleanup_2026-06-29_frontmatter\backups_before_encoding\10_qispark\10_QiSpark\00_QiCode`

## Coverage Summary

- Legacy files reviewed: `1`
- Exact matches: `1`
- Covered by QiCode text: `0`
- Partial review: `0`
- Missing review: `0`
- Binary review: `0`

## Structure Summary

- Required structure checks: `133`
- Missing required structure items: `0`

## Archive Rule

Only archive the old legacy folder if the decision says `SAFE TO ARCHIVE`, or if every `REVIEW_*` item has been manually marked as intentionally deprecated, duplicate, or preserved elsewhere.

Recommended archive move after a clean pass:

```powershell
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
Move-Item 'C:\QiLabs\50_QiLabs' "C:\QiLabs\90_QiArchive\legacy\50_QiLabs_$stamp"
```

Do not delete the archive. Move it. Future Cody will thank present Cody.
