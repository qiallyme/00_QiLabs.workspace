# QiLabs Issue Labels

Use these labels to keep Codex work controlled, sortable, and not chaotic.

## Priority Labels

- `priority:P0` — Blocking production, data safety, or deployment
- `priority:P1` — High-leverage active build item
- `priority:P2` — Important but not blocking
- `priority:P3` — Later cleanup, polish, or backlog

## App Labels

- `app:QiFinance`
- `app:QiTarot`
- `app:QiLife`
- `app:QiCare`
- `app:QiSpark`
- `app:QiLegal`
- `app:QiTrials`
- `app:QiServer`
- `app:VideoTooling`

## Work Mode Labels

- `mode:audit`
- `mode:architecture`
- `mode:patch`
- `mode:migration`
- `mode:ui-polish`
- `mode:test`
- `mode:cleanup`

## Status Labels

- `status:new`
- `status:ready-for-codex`
- `status:in-progress`
- `status:needs-review`
- `status:blocked`
- `status:done`

## Risk Labels

- `risk:low`
- `risk:medium`
- `risk:high`
- `risk:production`
- `risk:sensitive-data`

## Data / Infrastructure Labels

- `data:supabase`
- `data:rls`
- `data:migration`
- `data:tax`
- `data:finance`
- `data:legal`
- `data:care`
- `infra:cloudflare`
- `infra:github`
- `infra:tailscale`
- `infra:device-fleet`

## Recommended Minimum Label Set Per Issue

Every issue should have:

1. One app label
2. One priority label
3. One mode label
4. One risk label
5. `status:ready-for-codex` only when it has enough detail for Codex to work

Example:

`app:QiTarot`, `priority:P1`, `mode:patch`, `risk:medium`, `data:supabase`, `status:ready-for-codex`
