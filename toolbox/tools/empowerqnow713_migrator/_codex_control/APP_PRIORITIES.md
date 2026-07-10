# Qi App Priorities

## Current Priority Order

1. QiFinance
2. QiTarot
3. QiLife
4. QiCare
5. QiSpark
6. QiLegal
7. QiTrials
8. Video Tooling
9. QiServer / Fleet

---

## Priority 1: QiFinance

### Why it matters

QiFinance supports real financial organization, tax readiness, business cleanup, client potential, and future product value.

### Immediate focus

- Audit existing app/schema/import flow
- Determine persistence model
- Design transaction ingestion
- Design import review queue
- Preserve raw imports
- Normalize transactions
- Separate inflows and outflows
- Prepare tax-history module design

### Do not do yet

- Do not make public release decisions
- Do not import sensitive real records into unsafe demo tables
- Do not add AI automation before review/audit trail exists
- Do not run production migrations without approval

---

## Priority 2: QiTarot

### Why it matters

QiTarot is closest to public-product shape.

### Immediate focus

- Fix readings persistence
- Verify people/reader links
- Verify reading history survives refresh
- Polish carousel/step hierarchy/mobile layout
- Prepare release hardening checklist

### Do not do yet

- Do not add OCR/photo workflow before persistence is stable
- Do not add voice readout before base reading save flow is reliable
- Do not do a full redesign

---

## Priority 3: QiLife

### Why it matters

QiLife can become the daily personal command center.

### Immediate focus

- Smoke test revamped app
- Verify auth/persistence
- Verify dashboard works
- Document blockers

### Do not do yet

- Do not expand modules before smoke testing
- Do not build giant cockpit logic until core records are stable

---

## Priority 4: QiCare

### Why it matters

QiCare could become a caregiver-support product.

### Immediate focus

- Define MVP
- Audit existing care records/schemas
- Identify safe patient/caregiver data model
- Create doctor/family summary concept

### Do not do yet

- Do not publicize without privacy/security review
- Do not use real patient data in demos

---

## Priority 5: QiSpark

### Why it matters

QiSpark is the front door.

### Immediate focus

- Keep stable
- Links/bookmarks/dashboard cards
- App entry points
- Status cards

### Do not do yet

- Do not turn QiSpark into the cockpit
- Do not overload it with every system control

---

## Priority 6: QiLegal

### Why it matters

QiLegal could be powerful but dangerous if vague.

### Immediate focus

- Audit what exists
- Define product boundary
- Identify personal vs public vs client use
- Define evidence/timeline/filing model

### Do not do yet

- Do not build marketplace app before scope lock
- Do not expose sensitive legal material

---

## Priority 7: QiTrials

### Why it matters

QiTrials is useful as a laboratory.

### Immediate focus

- Inspect for reusable components
- Copy good ideas into active apps when approved
- Archive dead experiments

### Do not do yet

- Do not treat experiments as production obligations

---

## Priority 8: Video Tooling

### Why it matters

Video scripts are scattered and should eventually become coherent.

### Immediate focus

- Inventory scripts
- Define one simple video tool:
  - combine clips
  - convert formats
  - normalize filenames
  - export clean output

### Do not do yet

- Do not build a giant editor

---

## Priority 9: QiServer / Fleet

### Why it matters

Device onboarding and server reinstall need a repeatable pattern.

### Immediate focus

- Keep bootstrap scripts clean
- Prepare new-server checklist
- Prepare Tailscale/device enrollment flow
- Prepare new-laptop install path

### Do not do yet

- Do not let this distract from QiFinance/QiTarot unless infrastructure blocks work
