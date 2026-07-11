[CmdletBinding()]
param(
    [string]$BibleFolderName = "00_bible"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Get-Location).Path
$BiblePath = Join-Path $ProjectRoot $BibleFolderName

$Templates = [ordered]@{
    "_index.md" = @'
---
title: Story Bible
content_project:
content_project_type:
status: active
tags:
  - story-bible
---

# Story Bible

## Bible Files

- [[01_project_identity]]
- [[02_core_thesis_and_purpose]]
- [[03_manifesto]]
- [[04_audience]]
- [[05_themes_and_motifs]]
- [[06_voice_and_style]]
- [[07_canon_and_boundaries]]
- [[08_structure_and_outline]]
- [[09_content_map]]
- [[10_seed_bank]]
- [[11_research_and_sources]]
- [[12_glossary]]
- [[13_connections]]
- [[14_publishing_notes]]
- [[15_continuity_log]]

## Project Snapshot

**Project:**  
**Type:** Series / Book / Other  
**Umbrella:** EmpowerQNow  
**Primary platform:** QSaysIt  
**Current phase:**  
**Next decision:**  
'@

    "01_project_identity.md" = @'
---
title: Project Identity
tags:
  - story-bible
  - project-identity
---

# Project Identity

**Project name:**  
**Project type:** Series / Book / Other  
**Umbrella:** EmpowerQNow  
**Primary platform:** QSaysIt  
**Status:**  
**One-sentence identity:**  

## What This Project Is

## What This Project Is Not

## Why It Belongs Under EmpowerQNow

## Distinguishing Features
'@

    "02_core_thesis_and_purpose.md" = @'
---
title: Core Thesis and Purpose
tags:
  - story-bible
  - thesis
---

# Core Thesis and Purpose

## Core Thesis

What central truth, question, tension, or idea governs this project?

## Purpose

Why does this project exist?

## Reader Outcome

What should the reader see, question, understand, feel, or do differently?

## Central Questions

- 
- 
- 
'@

    "03_manifesto.md" = @'
---
title: Manifesto
tags:
  - story-bible
  - manifesto
---

# Manifesto

## What We Believe

## What We Refuse

## What We Protect

## What We Challenge

## What This Project Makes Possible

## Governing Declaration
'@

    "04_audience.md" = @'
---
title: Audience
tags:
  - story-bible
  - audience
---

# Audience

## Primary Audience

## Secondary Audience

## What They Are Carrying

## What They Need

## What They May Resist

## What We Never Assume About Them
'@

    "05_themes_and_motifs.md" = @'
---
title: Themes and Motifs
tags:
  - story-bible
  - themes
  - motifs
---

# Themes and Motifs

## Primary Themes

- 
- 
- 

## Secondary Themes

- 
- 
- 

## Recurring Motifs

- 
- 
- 

## Symbols and Images

- 
- 
- 

## Recurring Questions

- 
- 
- 
'@

    "06_voice_and_style.md" = @'
---
title: Voice and Style
tags:
  - story-bible
  - voice
  - style
---

# Voice and Style

## Voice

## Tone

## Emotional Range

## Structural Habits

## Language to Favor

## Language to Avoid

## Formatting Conventions

## Representative Passages
'@

    "07_canon_and_boundaries.md" = @'
---
title: Canon and Boundaries
tags:
  - story-bible
  - canon
  - continuity
---

# Canon and Boundaries

## Canonical Truths

- 
- 
- 

## Boundaries

- 
- 
- 

## Things This Project Does Not Claim

- 
- 
- 

## Continuity Rules

- 
- 
- 

## Open Canon Questions

- 
- 
- 
'@

    "08_structure_and_outline.md" = @'
---
title: Structure and Outline
tags:
  - story-bible
  - structure
  - outline
---

# Structure and Outline

## Project Shape

### Series

- Series premise:
- Recurring formats:
- Installment categories:
- Reading order:

### Book

- Book premise:
- Part structure:
- Chapter progression:
- Narrative or argumentative arc:

## Current Outline

1. 
2. 
3. 

## Structural Decisions

| Date | Decision | Reason |
|---|---|---|
|  |  |  |
'@

    "09_content_map.md" = @'
---
title: Content Map
tags:
  - story-bible
  - content-map
---

# Content Map

| ID | Working title | Type | Status | Core idea | Related theme | Canonical path |
|---|---|---|---|---|---|---|
| 001 |  |  | seed |  |  |  |
'@

    "10_seed_bank.md" = @'
---
title: Seed Bank
tags:
  - story-bible
  - seeds
---

# Seed Bank

## Raw Seeds

- 

## Developed Seeds

- 

## Unresolved Questions

- 

## Possible Titles

- 

## Fragments Worth Preserving

- 
'@

    "11_research_and_sources.md" = @'
---
title: Research and Sources
tags:
  - story-bible
  - research
  - sources
---

# Research and Sources

## Project-Specific Sources

- 

## Shared EmpowerQNow Sources

- 

## Sources Requiring Verification

- 

## Research Gaps

- 

## Citation Notes
'@

    "12_glossary.md" = @'
---
title: Glossary
tags:
  - story-bible
  - glossary
---

# Glossary

| Term | Meaning in this project | Related term or source |
|---|---|---|
|  |  |  |
'@

    "13_connections.md" = @'
---
title: Connections
tags:
  - story-bible
  - connections
---

# Connections

## Related Series

- 

## Related Books

- 

## Shared EmpowerQNow Frameworks

- 

## Companion Posts

- 

## Cross-Series Continuity

- 
'@

    "14_publishing_notes.md" = @'
---
title: Publishing Notes
tags:
  - story-bible
  - publishing
---

# Publishing Notes

**Primary destination:** QSaysIt  
**Series/category label:**  
**Expected formats:**  
**Cross-posting notes:**  
**Media needs:**  
**SEO or metadata notes:**  

## Publication Rules

## Platform-Specific Notes
'@

    "15_continuity_log.md" = @'
---
title: Continuity Log
tags:
  - story-bible
  - continuity-log
---

# Continuity Log

| Date | Decision or change | Reason | Files affected |
|---|---|---|---|
|  |  |  |  |
'@
}

if (-not (Test-Path -LiteralPath $BiblePath)) {
    New-Item -ItemType Directory -Path $BiblePath | Out-Null
    Write-Host "Created folder: $BiblePath"
}
else {
    Write-Host "Folder already exists: $BiblePath"
}

$Created = 0
$Skipped = 0

foreach ($FileName in $Templates.Keys) {
    $TargetPath = Join-Path $BiblePath $FileName

    if (Test-Path -LiteralPath $TargetPath) {
        Write-Host "Skipped existing file: $FileName"
        $Skipped++
        continue
    }

    $Templates[$FileName] | Set-Content -LiteralPath $TargetPath -Encoding UTF8
    Write-Host "Created: $FileName"
    $Created++
}

Write-Host ""
Write-Host "Story bible complete."
Write-Host "Created: $Created"
Write-Host "Skipped: $Skipped"
Write-Host "Location: $BiblePath"
