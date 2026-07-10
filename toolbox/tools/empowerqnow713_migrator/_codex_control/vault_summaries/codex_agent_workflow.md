# Qi Codex Agent Workflow Summary

Date: 2026-07-07

## Summary

The Qi ecosystem will use a controlled agentic development workflow.

GitHub/QiLabs issues are the primary execution queue.

The Codex folder at `60_QiApps/67_QiCodex/` is the local operating manual for agent behavior, templates, safety rules, and project priorities.

The Qi Vault is the strategic memory layer. It stores app summaries, product direction, architectural decisions, and meaningful status updates.

Pull requests and commits are the implementation record.

## Operating model

Codex should work one issue at a time, preferably from a clearly scoped issue with acceptance criteria, allowed changes, forbidden changes, and test steps.

Codex should operate in explicit modes:

- Audit
- Architecture
- Patch
- Migration
- UI Polish
- Test
- Cleanup

## Current project priority order

1. QiFinance
2. QiTarot
3. QiLife
4. QiCare
5. QiSpark
6. QiLegal
7. QiTrials
8. Video tooling
9. QiServer / Fleet tooling

## Strategic notes

QiFinance is the highest priority because it supports transaction cleanup, financial organization, tax-history records, AI-assisted categorization, deduction tracking, rules, analytics, and future product potential.

QiTarot is second priority because it is closest to production but still needs Supabase persistence verification and UI polish.

QiLife should be smoke-tested before expansion.

QiCare needs a coherent MVP definition before serious building.

QiSpark should remain the stable front door of the Qi ecosystem, not a bloated replacement cockpit.

QiLegal needs an audit before product decisions.

QiTrials should be mined for useful experiments, not treated as a production app.

## Safety doctrine

Codex must inspect first, explain second, patch third, test fourth, and document fifth.

Codex must not run destructive migrations, overwrite secrets, delete production data, or make broad architectural changes without review.

Core operating rule:

> Inspect first. Patch small. Migrate last. Commit often.
