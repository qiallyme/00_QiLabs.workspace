# Qi Codex Control Center

## Purpose

This document defines how Codex/local agentic coding should operate inside the Qi ecosystem.

The goal is not to let the agent freely modify every project. The goal is to use Codex as a controlled engineering assistant that can inspect, plan, patch, test, document, and update issues without damaging production systems, overwriting important work, or creating architectural chaos.

Codex should treat GitHub/QiLabs issues as the primary execution queue.

This folder exists to define operating rules, project priorities, work-order structure, and vault-sync expectations.

---

## 1. Operating Principle

Codex does not own the system.

Codex assists with:

- auditing projects
- identifying broken flows
- writing small patches
- generating migrations
- running tests
- cleaning dead code after review
- improving UI based on specific requests
- updating issues with findings
- producing summaries for the Qi Vault

Codex should not make broad architectural decisions without review.

Default mode:

> Inspect first. Explain second. Patch third. Test fourth. Document fifth.

---

## 2. Source of Truth Hierarchy

| Layer | Purpose | Source of truth for |
|---|---|---|
| GitHub / QiLabs Issues | Execution queue | What Codex should work on next |
| `60_QiApps/67_QiCodex/` | Agent instructions + work-order templates | How Codex should behave |
| `40_QiVault/` | Strategic memory | Why we are building it and where each app stands |
| Pull requests / commits | Implementation record | What changed |

### 2.1 GitHub / QiLabs Issues

Issues are the execution source of truth.

Use issues for:

- specific bugs
- features
- migrations
- UI polish passes
- audits
- app-hardening tasks
- deployment tasks
- release-readiness checklists

Codex should work from one issue at a time whenever possible.

Each issue should include:

- app name
- task summary
- current problem
- desired result
- files likely involved
- allowed changes
- forbidden changes
- acceptance criteria
- test steps
- documentation update requirements

### 2.2 Codex Folder

`60_QiApps/67_QiCodex/` is the operating manual.

Use it for:

- agent rules
- work-order templates
- issue templates
- priority maps
- recurring safety rules
- system architecture notes
- vault-sync templates
- issue seed files

Do not use this folder as the primary backlog. The issue tracker is the backlog.

### 2.3 Qi Vault Markdown

The Qi Vault is the strategic memory layer.

Use the vault for:

- app summaries
- product doctrine
- long-term roadmap
- architecture decisions
- weekly status snapshots
- important unresolved questions
- links to key issues and pull requests

The vault should not contain every tiny bug. The vault should contain the meaningful pattern.

### 2.4 Pull Requests / Commits

Pull requests and commits are the implementation record.

Every meaningful code change should be traceable to:

- one issue
- one branch
- one summary
- one test result
- one vault update if strategically relevant

---

## 3. Current Project Priority Order

1. QiFinance
2. QiTarot
3. QiLife
4. QiCare
5. QiSpark
6. QiLegal
7. QiTrials
8. Video tooling
9. QiServer / Fleet tooling

This order can change, but Codex should not reorder priorities by itself.

---

## 4. App Purposes

### 4.1 QiFinance

QiFinance is the financial records, transaction ingestion, analytics, rules, automation, and tax-history system.

Primary goals:

- import financial files
- normalize transactions
- separate inflows and outflows
- preserve raw imports
- categorize transactions
- suggest rules
- track deductions
- manage historical tax records
- support yearly comparison
- export records for tax preparation
- eventually support client records safely

QiFinance is high priority because it supports real money, legal recordkeeping, business organization, and future product potential.

### 4.2 QiTarot

QiTarot is a tarot reading tracker and interpretation app.

Primary goals:

- store spreads
- store cards
- store readings
- associate readings with people/readers
- support reading history
- support spread order
- support AI interpretation
- eventually support photo capture, OCR, voice readout, and deeper reading analytics

Immediate known issue:

- Cards and spreads exist in the database, but readings and person-related records may not be persisting to Supabase correctly.

QiTarot is close to production but still needs persistence verification, UI polish, and release hardening.

### 4.3 QiLife

QiLife is the personal operating system for tracking life records, tasks, routines, decisions, and personal status.

Primary goals:

- track personal records
- organize life domains
- support dashboard-style review
- connect later to other Qi systems
- become useful as a daily command center

QiLife should be tested before additional expansion.

### 4.4 QiCare

QiCare is the caregiving and patient-care tracking app.

Primary goals:

- help caregivers track patient needs
- document care activities
- organize medications, appointments, symptoms, incidents, family notes, and doctor-relevant updates
- produce useful summaries for family members and care providers

QiCare may become a sellable caregiver-support app, but it needs a coherent MVP definition before heavy building.

### 4.5 QiSpark

QiSpark is the front door of the Qi ecosystem.

Primary goals:

- stable landing page
- dashboard links
- bookmarks
- quick access to apps
- contact/resource pointers
- system status summary
- starting point from any device

QiSpark should stay simple. It is not the full cockpit. It is the front door.

### 4.6 QiLegal

QiLegal is the legal records, filings, timelines, evidence, and case-support app.

Primary goals are not yet finalized.

Codex should audit QiLegal before building.

Questions to answer:

- Is this for personal legal cases?
- Is this for client/legal-document workflow?
- Is this for evidence timelines?
- Is this for dispute packets?
- Is this for marketplace/public use?
- What records are sensitive?
- What should never be exposed publicly?

No production build should begin until QiLegal has a clear product definition.

### 4.7 QiTrials

QiTrials is the experiments area.

Primary goals:

- store prototypes
- test ideas
- preserve useful experiments
- mine features for reuse

QiTrials should not be treated as a production app.

Codex may inspect QiTrials for reusable ideas, but should not try to finish every experiment.

### 4.8 Video Tooling

Video tooling includes scattered Python scripts and media utilities.

Primary goals:

- consolidate scripts
- define one coherent tool
- support basic video operations
- combine clips
- convert formats
- normalize outputs
- organize filenames

This should be cleaned later after core apps stabilize.

### 4.9 QiServer / Fleet

QiServer and fleet tooling support device management and infrastructure setup.

Primary goals:

- prepare server reinstall process
- document baseline server setup
- manage device onboarding
- support Tailscale setup
- install common software
- manage remote access tools
- create a repeatable new-device bootstrap process

This is important but should not distract from QiFinance and QiTarot unless infrastructure blocks deployment.

---

## 5. Codex Work Modes

Codex must operate in one mode at a time.

### 5.1 Audit Mode

Purpose:

- inspect structure
- identify current state
- find missing files
- find broken flows
- find duplicate code
- find unsafe patterns

Rules:

- do not edit code
- do not run destructive commands
- do not migrate databases
- produce findings and recommendations

### 5.2 Architecture Mode

Purpose:

- propose structure
- propose schemas
- propose component organization
- propose service boundaries
- propose deployment structure

Rules:

- do not implement yet
- explain tradeoffs
- identify risks
- propose smallest safe path

### 5.3 Patch Mode

Purpose:

- implement a small approved fix

Rules:

- one issue at a time
- one branch per issue
- smallest safe change
- preserve working features
- document changed files
- run tests/build where available

### 5.4 Migration Mode

Purpose:

- create database migration SQL

Rules:

- generate SQL first
- explain impact
- identify affected tables
- identify RLS implications
- do not run against production without approval
- include rollback notes when practical

### 5.5 UI Polish Mode

Purpose:

- fix specific interface issues

Rules:

- only touch requested UI areas
- do not rewrite app architecture
- preserve data flows
- test mobile layout where possible
- avoid decorative bloat

### 5.6 Test Mode

Purpose:

- run tests, builds, linting, and manual verification

Rules:

- report exact commands
- report exact failures
- do not hide failing tests
- distinguish confirmed fixes from assumptions

### 5.7 Cleanup Mode

Purpose:

- remove dead code, duplicates, unused files, stale configs

Rules:

- list proposed deletions first
- do not delete without review
- preserve experimental work unless explicitly approved
- move uncertain items to archive instead of deleting

---

## 6. Safety Rules

### 6.1 Database Safety

Codex must not:

- run destructive migrations without approval
- drop tables without approval
- delete production data
- overwrite Supabase policies casually
- expose secrets in client code
- treat localStorage as production persistence
- silently change auth assumptions

Codex must:

- preview migrations first
- explain RLS impact
- preserve raw imported records
- keep auditability for finance, legal, tax, care, and client records

### 6.2 Cloudflare Safety

Codex must not:

- overwrite production workers without review
- replace environment variables without review
- delete routes
- modify secrets casually
- deploy experimental branches to production

Codex must:

- identify deployment target
- distinguish preview from production
- document changed routes, bindings, secrets, and workers

### 6.3 Financial / Tax / Legal / Care Data Safety

These apps contain sensitive records.

Codex must treat the following as high-sensitivity:

- financial transactions
- tax records
- client tax records
- legal documents
- case timelines
- health/care notes
- caregiver logs
- identity documents
- addresses
- account numbers
- uploaded documents

Rules:

- no sensitive data in console logs
- no sensitive data in frontend debug output
- no test fixtures using real private data unless explicitly marked local/private
- no public demo data copied from real records
- no careless export endpoints

---

## 7. Git Workflow

Preferred branch naming:

- `codex/qifinance/issue-###-short-slug`
- `codex/qitarot/issue-###-short-slug`
- `codex/qilife/issue-###-short-slug`
- `codex/qicare/issue-###-short-slug`

Commit message format:

- `fix(qitarot): persist readings to Supabase`
- `feat(qifinance): add import review queue schema`
- `chore(qispark): clean dashboard links`
- `docs(codex): add work order template`

Each commit should connect to an issue where practical.

---

## 8. Issue Lifecycle

### New

Issue exists but has not been reviewed.

### Ready for Codex

Issue has enough context for Codex to start.

Must include:

- app
- task
- acceptance criteria
- allowed files or areas
- forbidden changes
- test steps or expected verification

### In Progress

Codex is actively working on the issue.

Codex should comment with:

- files inspected
- suspected cause
- intended patch
- branch name

### Needs Review

Codex has made changes and needs human review.

Codex should include:

- changed files
- summary of patch
- commands run
- test result
- risks
- screenshots if UI-related
- migration SQL if database-related

### Blocked

Codex cannot continue safely.

Blocked reasons may include:

- missing credentials
- unclear product decision
- failing dependency
- conflicting schema
- missing environment variables
- production risk
- unclear sensitive-data boundary

### Done

Issue can close only when acceptance criteria are satisfied or deliberately deferred with explanation.

---

## 9. Definition of Done

A Codex task is done when:

- the requested issue is addressed
- unrelated changes are avoided
- changed files are listed
- tests/builds are run where available
- manual test steps are provided
- database changes are documented
- deployment impact is documented
- issue is updated
- vault summary is created if strategically relevant

---

## 10. Vault Sync Rule

Codex should create a vault summary when a task affects:

- app purpose
- architecture
- database schema
- deployment
- product direction
- security model
- release readiness
- major feature status

Codex should not create vault summaries for tiny typo fixes unless they reveal a larger pattern.

Vault summary format:

```md
## App

## Date

## Issue / Branch

## What changed

## Why it matters

## Current status

## Remaining blockers

## Next recommended action
```

---

## 11. First Execution Priorities

### Priority 1: QiFinance Audit

Codex should inspect QiFinance and report:

- current structure
- current persistence model
- current import flow
- current Supabase usage
- missing tables
- missing migrations
- missing review queue
- missing tax record structure
- security concerns
- first safe implementation patch

No code changes until the audit is reviewed.

### Priority 2: QiTarot Persistence Fix

Codex should inspect QiTarot and determine:

- where readings are stored
- why readings are not saving to Supabase
- whether people/reading links exist
- whether RLS blocks inserts
- whether auth/session handling is missing
- whether localStorage is being used incorrectly
- smallest safe persistence patch

UI polish should happen after persistence is fixed.

### Priority 3: QiLife Smoke Test

Codex should verify:

- app builds
- app runs
- records persist
- core dashboard works
- obvious errors are documented

Do not expand QiLife until it is confirmed usable.

### Priority 4: QiSpark Scope Lock

Codex should define QiSpark as:

- front door
- dashboard
- bookmarks
- links
- status cards
- quick access

Codex should not turn QiSpark into a full replacement cockpit.

---

## 12. Core Instruction for Codex

When unsure, do not guess.

Stop and report:

- what is known
- what is unknown
- what is risky
- what needs a product decision
- what the smallest safe next step is

The system is allowed to be powerful.

It is not allowed to be sloppy.
