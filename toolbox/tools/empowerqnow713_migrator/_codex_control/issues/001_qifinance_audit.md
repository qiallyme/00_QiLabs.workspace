# [QiFinance] Audit current app, schema, imports, and persistence

## App

QiFinance

## Priority

P1

## Mode

Audit

## Problem

QiFinance needs a clear current-state audit before implementation. The app should become a Supabase-backed financial records, ingestion, rules, analytics, and tax-history system, but the current structure and persistence model need to be verified first.

## Desired Outcome

Produce a complete audit of the current QiFinance code, schema, migrations, import flow, UI, Supabase usage, and deployment assumptions. Do not modify code.

## Context

QiFinance is the highest priority because it supports transaction cleanup, financial organization, tax-history records, AI-assisted categorization, deduction tracking, rules, analytics, and future product potential.

## Allowed Changes

- Inspect QiFinance folders and docs
- Inspect Supabase migrations and SQL related to finance
- Inspect import scripts and CSV mappings
- Inspect package/build/deployment files
- Read README/setup docs

## Forbidden Changes

- Do not edit code
- Do not run migrations
- Do not modify secrets
- Do not deploy
- Do not delete or move files

## Likely Files / Areas

- 60_QiApps/*QiFinance*
- 20_QiServer/data/supabase
- 20_QiServer/QiMemory/_inbox/financial
- Supabase migrations
- CSV import scripts
- README files

## Acceptance Criteria

- [ ] Current structure is documented
- [ ] Persistence model is documented
- [ ] Existing finance schema/migrations are identified
- [ ] Import flow is documented
- [ ] Missing tables/features are listed
- [ ] Security risks are listed
- [ ] First safe implementation patch is proposed

## Test Steps

1. Run repository/file inspection only
2. Run build/test commands only if safe and non-destructive
3. Report exact commands used
4. Report exact failures or blockers

## Documentation Required

- Update issue with audit summary
- Create vault summary if architectural decisions are found

## Risk Level

Medium. Finance and tax data are sensitive. This is audit-only, so risk stays contained.

## Codex Starting Instruction

Start in audit mode.

Inspect the relevant files and report:

1. What exists
2. What is broken or missing
3. What files are involved
4. What patch you recommend
5. What risks exist

Do not edit until the intended patch is explained.
