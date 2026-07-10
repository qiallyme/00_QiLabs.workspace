# [QiTarot] UI polish pass for carousel, centering, mobile hierarchy

## App

QiTarot

## Priority

P2

## Mode

UI Polish

## Problem

QiTarot UI is improved but still has visible issues: title/description centering, spread selection behaving like a list instead of a swipe/card carousel, step headings needing stronger hierarchy, labels being too wordy, and mobile layout hiccups.

## Desired Outcome

Apply a focused UI polish pass only to the identified areas while preserving data flows and persistence.

## Context

UI polish should happen after or alongside the persistence fix, but it must not become a full redesign.

## Allowed Changes

- Inspect affected UI components
- Patch layout/styling for listed issues
- Improve mobile hierarchy
- Keep changes small

## Forbidden Changes

- Do not rewrite the app
- Do not touch persistence logic unless required for UI state
- Do not add OCR/voice features
- Do not change unrelated screens

## Likely Files / Areas

- QiTarot components
- QiTarot CSS/styling files
- spread selection UI
- home/header/step components

## Acceptance Criteria

- [ ] Title and short description are centered
- [ ] Spread selection feels like card/swipe carousel
- [ ] Step headings are clearer
- [ ] Labels are tightened
- [ ] Mobile layout is improved
- [ ] No persistence regressions are introduced

## Test Steps

1. Run the app locally
2. Check desktop layout
3. Check mobile/narrow viewport
4. Create a reading to ensure UI flow still works
5. Confirm no console errors

## Documentation Required

- Update issue with changed files and screenshots if possible
- Vault summary only if product/UI direction changes

## Risk Level

Medium. UI changes can accidentally break flow if overdone.

## Codex Starting Instruction

Start in audit mode.

Inspect the relevant files and report:

1. What exists
2. What is broken or missing
3. What files are involved
4. What patch you recommend
5. What risks exist

Do not edit until the intended patch is explained.
