# [QiTarot] Trace and fix readings not saving to Supabase

## App

QiTarot

## Priority

P1

## Mode

Patch

## Problem

Cards and spreads exist in the database, but readings, people, reading links, and related records may not be saving to Supabase. The app may be using browser/local state instead of true persistence.

## Desired Outcome

Trace the save/read flow and implement the smallest safe patch so readings persist to Supabase and survive refresh.

## Context

QiTarot is close to production but persistence must be trustworthy before UI polish, OCR, voice readout, or public release.

## Allowed Changes

- Inspect frontend save/read flow
- Inspect Supabase client usage
- Inspect qitarot migrations
- Inspect RLS policies if available
- Patch only the persistence path after explaining intended change

## Forbidden Changes

- Do not redesign the app
- Do not run destructive migrations
- Do not touch unrelated apps
- Do not use localStorage as fake persistence
- Do not silently bypass auth/RLS

## Likely Files / Areas

- QiTarot frontend components/services
- Supabase client
- 20_QiServer/data/supabase/qisupabase/migrations/20260706100000_qitarot.sql
- 20260706100441_qitarot_catalog_people_analytics.sql
- 20260707020000_qitarot_rating.sql

## Acceptance Criteria

- [ ] Codex identifies where readings are currently stored
- [ ] Root cause is documented
- [ ] Smallest persistence patch is explained before editing
- [ ] Readings save to Supabase
- [ ] Reading history loads after refresh
- [ ] Errors are visible instead of silent
- [ ] Manual test steps are provided

## Test Steps

1. Create a reading
2. Choose a spread
3. Assign person/Myself
4. Draw cards
5. Save reading
6. Refresh browser
7. Verify reading exists in Supabase
8. Verify reading history loads

## Documentation Required

- Update issue with patch summary
- Create vault summary if schema/data flow changed

## Risk Level

Medium to High. Persistence and Supabase/RLS are involved.

## Codex Starting Instruction

Start in audit mode.

Inspect the relevant files and report:

1. What exists
2. What is broken or missing
3. What files are involved
4. What patch you recommend
5. What risks exist

Do not edit until the intended patch is explained.
