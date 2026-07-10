# Codex Work Order Template

Use this template when creating a GitHub/QiLabs issue for Codex.

---

## Title

`[AppName] Short action-focused task title`

Example:

`[QiTarot] Fix readings not persisting to Supabase`

---

## App

QiFinance / QiTarot / QiLife / QiCare / QiSpark / QiLegal / QiTrials / QiServer / Video Tooling

---

## Priority

P0 / P1 / P2 / P3

- P0: Blocking production or data safety
- P1: High leverage / current active build
- P2: Important but not blocking
- P3: Later / cleanup / polish

---

## Mode

Audit / Architecture / Patch / Migration / UI Polish / Test / Cleanup

---

## Problem

Describe what is currently wrong.

---

## Desired Outcome

Describe what should be true when this issue is complete.

---

## Context

Add relevant product or technical context.

Include known observations, screenshots, errors, table names, file names, or prior decisions.

---

## Allowed Changes

Codex may modify:

- list folders
- list files
- list configs
- list migrations

---

## Forbidden Changes

Codex must not:

- run production migrations
- delete data
- rewrite unrelated UI
- touch unrelated apps
- modify secrets
- change deployment targets
- remove experimental work without review

Add any task-specific restrictions here.

---

## Likely Files / Areas

Possible areas involved:

- frontend components
- Supabase client
- migrations
- API worker
- Cloudflare config
- import scripts
- shared packages
- docs

---

## Acceptance Criteria

This issue is complete when:

- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3
- [ ] Tests/builds pass or failures are documented
- [ ] Manual test steps are provided
- [ ] Issue is updated with summary
- [ ] Vault summary is created if strategically relevant

---

## Test Steps

Codex should verify by:

1. Step one
2. Step two
3. Step three

---

## Documentation Required

Codex should update:

- README
- Qi Vault summary
- schema docs
- setup docs
- deployment notes
- none

---

## Risk Level

Low / Medium / High

Explain why.

---

## Codex Starting Instruction

Start in audit mode.

Inspect the relevant files and report:

1. What exists
2. What is broken or missing
3. What files are involved
4. What patch you recommend
5. What risks exist

Do not edit until the intended patch is explained.
