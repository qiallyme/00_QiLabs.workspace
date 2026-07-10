# [QiLife] Smoke test current revamped app

## App

QiLife

## Priority

P1

## Mode

Test

## Problem

QiLife was recently revamped and needs verification before expansion. The app should be tested for build, run, core dashboard behavior, auth/persistence, and obvious errors.

## Desired Outcome

Run a focused smoke test and document what works, what fails, and the next smallest safe patch.

## Context

QiLife can become the daily command center, but expanding before testing would be sloppy.

## Allowed Changes

- Inspect QiLife app folders
- Run install/build/test commands if available
- Run local app if safe
- Inspect Supabase migration usage
- Document failures

## Forbidden Changes

- Do not expand features
- Do not redesign
- Do not run production migrations
- Do not change auth without review

## Likely Files / Areas

- 60_QiApps/61_QiLife/qilife.2
- QiLife src/features/qilife
- QiLife Supabase migrations
- QiLife README/docs

## Acceptance Criteria

- [ ] Build status is documented
- [ ] Run status is documented
- [ ] Auth/persistence assumptions are documented
- [ ] Core dashboard status is documented
- [ ] Errors are listed
- [ ] Next safe patch is proposed

## Test Steps

1. Install dependencies if needed
2. Run build
3. Run dev server if safe
4. Open main flow
5. Create/test a record if local/dev safe
6. Report failures

## Documentation Required

- Update issue with smoke test report
- Create vault summary if blockers affect roadmap

## Risk Level

Medium. App testing may expose env/auth/deployment issues.

## Codex Starting Instruction

Start in audit mode.

Inspect the relevant files and report:

1. What exists
2. What is broken or missing
3. What files are involved
4. What patch you recommend
5. What risks exist

Do not edit until the intended patch is explained.
