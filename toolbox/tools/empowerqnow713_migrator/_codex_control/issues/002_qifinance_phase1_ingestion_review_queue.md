# [QiFinance] Design Phase 1 transaction ingestion and review queue

## App

QiFinance

## Priority

P1

## Mode

Architecture

## Problem

QiFinance needs a safe Phase 1 architecture for importing financial files, preserving raw imports, normalizing transactions, detecting duplicates, and creating a user review queue before data becomes final.

## Desired Outcome

Design the minimum viable Phase 1 architecture and migration plan for transaction ingestion and review. Generate SQL/migration proposals only; do not run them.

## Context

Core product idea: drop financial chaos in, get clean books, categories, deductions, reports, and tax-ready records out.

## Allowed Changes

- Inspect existing finance schemas
- Propose tables
- Propose review states
- Propose duplicate detection strategy
- Propose raw import preservation model
- Propose RLS/security notes

## Forbidden Changes

- Do not run migrations
- Do not rewrite app
- Do not import real data
- Do not add AI automation yet
- Do not expose sensitive records

## Likely Files / Areas

- Supabase migrations
- finance import scripts
- transaction taxonomy docs
- qifinance reserved schema docs
- QiFinance frontend import flow

## Acceptance Criteria

- [ ] Phase 1 architecture is documented
- [ ] Tables are proposed
- [ ] Review queue lifecycle is defined
- [ ] Raw import preservation is defined
- [ ] Duplicate strategy is defined
- [ ] RLS/security notes are included
- [ ] First implementation patch is identified

## Test Steps

1. Validate proposed SQL syntax locally if possible without touching production
2. List migration order
3. List rollback/repair notes where practical

## Documentation Required

- Update issue with architecture summary
- Update vault with QiFinance Phase 1 architecture summary

## Risk Level

High. This touches finance/tax architecture and future migrations.

## Codex Starting Instruction

Start in audit mode.

Inspect the relevant files and report:

1. What exists
2. What is broken or missing
3. What files are involved
4. What patch you recommend
5. What risks exist

Do not edit until the intended patch is explained.
