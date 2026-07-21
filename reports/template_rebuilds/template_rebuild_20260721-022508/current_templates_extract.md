# Current Template Extract

- Source: `C:\QiLabs\40_QiVault\_qiconfig\templates`
- Generated: `2026-07-21T02:25:08`

---

## _index.md

```text
---
title: "Templates"
type: index
status: active
generated_by: qilabs-housekeeping
generated_at: "20260701-200047"
layout: page
slug: ""
summary: ""
created_at: ""
updated_at: ""
author: ""
owner: ""
tags: []
keywords: []
aliases: []
context: ""
sensitivity: internal
classification: business_internal
realm_label: ""
uid: ""
canonical_ref: ""
source_type: manual
template_key: master-template
index_scope: ""
---

# Templates

<!-- QILABS:HOUSEKEEPING_INDEX_START -->

## Housekeeping Index

- [[Templates/Complete_Legal_Estate_Package|Complete Legal Estate Package]]

<!-- QILABS:HOUSEKEEPING_INDEX_END -->

```

---

## activity.md

```text
---
layout: template
type: activity
title: {{name}}
slug: name
status: active
updated_at: "2026-06-29"
tags:
  - cadence
source_type: imported
subject: {{name}}
summary: ""
created_at: ""
author: ""
owner: ""
keywords: []
aliases: []
context: ""
sensitivity: internal
classification: business_internal
realm_label: ""
uid: ""
canonical_ref: ""
template_key: master-template
---

# {{name}}


## Notes #notes

_Context and general notes..._

```

---

## asset.md

```text
---
layout: template
title: {{name}}
slug: name
status: ['active']
updated_at: "2026-06-29"
tags:
  - cadence
source_type: imported
name: {{name}}
asset_type:
  - device
type: asset
summary: ""
created_at: ""
author: ""
owner: ""
keywords: []
aliases: []
context: ""
sensitivity: internal
classification: business_internal
realm_label: ""
uid: ""
canonical_ref: ""
template_key: master-template
---

# {{name}}


## Notes #notes

_Context and general notes..._

```

---

## case.md

```text
---
layout: template
title: {{name}}
slug: name
status: ['active']
updated_at: "2026-06-29"
tags:
  - cadence
source_type: imported
priority:
  - medium
type: case
summary: ""
created_at: ""
author: ""
owner: ""
keywords: []
aliases: []
context: ""
sensitivity: internal
classification: business_internal
realm_label: ""
uid: ""
canonical_ref: ""
template_key: master-template
---

# {{name}}


## Notes #notes

_Context and general notes..._

```

---

## certification.md

```text
---
layout: template
title: {{name}}
slug: name
status: active
updated_at: "2026-06-29"
tags:
  - cadence
source_type: imported
name: {{name}}
type: certification
summary: ""
created_at: ""
author: ""
owner: ""
keywords: []
aliases: []
context: ""
sensitivity: internal
classification: business_internal
realm_label: ""
uid: ""
canonical_ref: ""
template_key: master-template
---

# {{name}}


## Notes #notes

_Context and general notes..._

```

---

## commission.md

```text
---
layout: template
title: {{name}}
slug: name
status: active
updated_at: "2026-06-29"
tags:
  - cadence
source_type: imported
reference: {{name}}
amount: 0
type: commission
summary: ""
created_at: ""
author: ""
owner: ""
keywords: []
aliases: []
context: ""
sensitivity: internal
classification: business_internal
realm_label: ""
uid: ""
canonical_ref: ""
template_key: master-template
---

# {{name}}


## Notes #notes

_Context and general notes..._

```

---

## company.md

```text
---
layout: template
title: {{name}}
slug: name
status: active
updated_at: "2026-06-29"
tags:
  - cadence
source_type: imported
name: {{name}}
type: company
summary: ""
created_at: ""
author: ""
owner: ""
keywords: []
aliases: []
context: ""
sensitivity: internal
classification: business_internal
realm_label: ""
uid: ""
canonical_ref: ""
template_key: master-template
---

# {{name}}


## Description #notes

_Company description and profile..._

## Contacts #cross-contact-company-table

## Deals #cross-deal-company-kanban

```

---

## contact.md

```text
---
layout: template
title: {{name}}
slug: name
status: active
updated_at: "2026-06-29"
tags:
  - cadence
source_type: imported
name: {{name}}
type: contact
summary: ""
created_at: ""
author: ""
owner: ""
keywords: []
aliases: []
context: ""
sensitivity: internal
classification: business_internal
realm_label: ""
uid: ""
canonical_ref: ""
template_key: master-template
---

# {{name}}


## Bio #notes

_Background, interests, and how we met..._

## Tasks #tasks

- [ ] Follow up in 2 weeks

```

---

## daily.md

```text
---
layout: page
type: daily
title: "{{date}}"
slug: "{{date}}"
summary: ""
status: active
visibility: internal
publish_target: none
publish_url: ""
created_at: "{{date}} {{time}}"
updated_at: "{{date}} {{time}}"
author: Cody J. Rice-Velasquez
owner: Cody
nav_title: "{{date}}"
nav_group: daily
nav_order: 999
nav_hidden: true
is_index: false
parent_ref: "[[10_daily/_index]]"
sensitivity: internal
classification: business_internal
realm_label: ""
tags: [daily]
keywords: []
aliases: []
context: ""
uid: ""
canonical_ref: ""
source_type: manual
template_key: master-template
---

# {{date}}

## Focus

- [ ]

## Schedule and tasks

![[TaskNotes/Views/agenda-default.base]]

## Notes

## Events to promote to the timeline

Create important events with the `event` template rather than turning the entire daily note into an event.

```

---

## deal.md

```text
---
layout: template
title: {{name}}
slug: name
status: active
updated_at: "2026-06-29"
tags:
  - cadence
source_type: imported
stage:
  - Lead
value: 0
type: deal
summary: ""
created_at: ""
author: ""
owner: ""
keywords: []
aliases: []
context: ""
sensitivity: internal
classification: business_internal
realm_label: ""
uid: ""
canonical_ref: ""
template_key: master-template
---

# {{name}}


## Notes #notes

_Context and general notes..._

```

---

## event.md

```text
---
layout: page
type: event
title: "{{title}}"
slug: "{{title}}"
summary: ""
status: active
visibility: internal
publish_target: none
publish_url: ""
created_at: "{{date}} {{time}}"
updated_at: "{{date}} {{time}}"
author: Cody J. Rice-Velasquez
owner: Cody
nav_title: "{{title}}"
nav_group: timeline
nav_order: 999
nav_hidden: true
is_index: false
parent_ref: "[[10_daily/_index]]"
sensitivity: internal
classification: business_internal
realm_label: ""
tags: [event]
keywords: []
aliases: []
context: ""
uid: ""
canonical_ref: ""
source_type: manual
template_key: master-template
date: "{{date}}"
event_type: ""
people: []
location: ""
significance: normal
canonical: false
timeline_include: false
timeline_status: unreviewed
---

# {{title}}

## What happened

## Why it matters

## People and place

## Sources

## Timeline review

- [ ] Date confirmed
- [ ] People and location confirmed
- [ ] Duplicate/canonical status reviewed
- [ ] Source linked
- [ ] Set `canonical: true` and `timeline_include: true` only when ready

```

---

## knowledge.md

```text
---
layout: template
title: {{name}}
slug: name
status: ['seed']
updated_at: "2026-06-29"
tags:
  - cadence
source_type: imported
knowledge_type:
  - doctrine
type: knowledge
summary: ""
created_at: ""
author: ""
owner: ""
keywords: []
aliases: []
context: ""
sensitivity: internal
classification: business_internal
realm_label: ""
uid: ""
canonical_ref: ""
template_key: master-template
---

# {{name}}


## Notes #notes

_Context and general notes..._

```

---

## lead.md

```text
---
layout: template
title: {{name}}
slug: name
status: active
updated_at: "2026-06-29"
tags:
  - cadence
source_type: imported
name: {{name}}
type: lead
summary: ""
created_at: ""
author: ""
owner: ""
keywords: []
aliases: []
context: ""
sensitivity: internal
classification: business_internal
realm_label: ""
uid: ""
canonical_ref: ""
template_key: master-template
---

# {{name}}


## Notes #notes

_Context and general notes..._

```

---

## master_template.md

```text
---
layout: page
type: note
title: "{{title}}"
slug: "{{title}}"
summary: ""
status: active
visibility: internal
publish_target: none
publish_url: /{{title}}
created_at: "{{date}} {{time}}"
updated_at: "{{date}} {{time}}"
author: Cody J. Rice-Velasquez
owner: Cody
nav_title: "{{title}}"
nav_group: ""
nav_order: 999
nav_hidden: false
is_index: false
parent_ref: ""
sensitivity: internal
classification:
  - blog-post
realm_label:
  - empowerqnow
tags:
  - EmpowerQNow
keywords: []
aliases: []
context: ""
uid: ""
canonical_ref: ""
source_type: manual
template_key: master-template
date: ""
event_type: ""
people: []
location: ""
significance: normal
canonical: false
timeline_include: false
timeline_status: unreviewed
---

# {{title}}

## Overview

## Key Information

## Notes / Actions

```

---

## output.md

```text
---
layout: template
title: {{name}}
slug: name
status: ['idea']
updated_at: "2026-06-29"
tags:
  - cadence
source_type: imported
output_type:
  - draft
type: output
summary: ""
created_at: ""
author: ""
owner: ""
keywords: []
aliases: []
context: ""
sensitivity: internal
classification: business_internal
realm_label: ""
uid: ""
canonical_ref: ""
template_key: master-template
---

# {{name}}


## Notes #notes

_Context and general notes..._

```

---

## partner.md

```text
---
layout: template
title: {{name}}
slug: name
status: active
updated_at: "2026-06-29"
tags:
  - cadence
source_type: imported
name: {{name}}
type: partner
summary: ""
created_at: ""
author: ""
owner: ""
keywords: []
aliases: []
context: ""
sensitivity: internal
classification: business_internal
realm_label: ""
uid: ""
canonical_ref: ""
template_key: master-template
---

# {{name}}


## Notes #notes

_Context and general notes..._

```

---

## place.md

```text
---
layout: template
title: {{name}}
slug: name
status: ['active']
updated_at: "2026-06-29"
tags:
  - cadence
source_type: imported
name: {{name}}
place_type:
  - home
type: place
summary: ""
created_at: ""
author: ""
owner: ""
keywords: []
aliases: []
context: ""
sensitivity: internal
classification: business_internal
realm_label: ""
uid: ""
canonical_ref: ""
template_key: master-template
---

# {{name}}


## Notes #notes

_Context and general notes..._

```

---

## project.md

```text
---
layout: template
title: {{name}}
slug: name
status: ['active']
updated_at: "2026-06-29"
tags:
  - cadence
source_type: imported
type: project
name: {{name}}
priority:
  - medium
started: 2026-06-27
summary: ""
created_at: ""
author: ""
owner: ""
keywords: []
aliases: []
context: ""
sensitivity: internal
classification: business_internal
realm_label: ""
uid: ""
canonical_ref: ""
template_key: master-template
project: ""
next_action: ""
due_date: ""
---

# {{name}}

## Brief

_The outcome we want, why now._


## Scope

**In scope:**
-

**Out of scope:**
-

## Milestones

- [ ] 2026-06-27 — First milestone

## Tasks

- [ ]

## Risks

-

## Stakeholders

-

## Notes

```

---

## record.md

```text
---
layout: template
title: {{name}}
slug: name
status: ['inbox']
updated_at: "2026-06-29"
tags:
  - cadence
source_type: imported
record_type:
  - document
evidence_level:
  - screenshot
type: record
summary: ""
created_at: ""
author: ""
owner: ""
keywords: []
aliases: []
context: ""
sensitivity: internal
classification: business_internal
realm_label: ""
uid: ""
canonical_ref: ""
template_key: master-template
record_date: ""
entities: ""
evidence: ""
financial_impact: ""
legal_relevance: ""
---

# {{name}}


## Notes #notes

_Context and general notes..._

```

---

## registration.md

```text
---
layout: template
title: {{name}}
slug: name
status: active
updated_at: "2026-06-29"
tags:
  - cadence
source_type: imported
value: 0
type: registration
summary: ""
created_at: ""
author: ""
owner: ""
keywords: []
aliases: []
context: ""
sensitivity: internal
classification: business_internal
realm_label: ""
uid: ""
canonical_ref: ""
template_key: master-template
---

# {{name}}


## Notes #notes

_Context and general notes..._

```

---

## sequence.md

```text
---
layout: template
title: {{name}}
slug: name
status: active
updated_at: "2026-06-29"
tags:
  - cadence
source_type: imported
name: {{name}}
steps: 0
active: 0
type: sequence
summary: ""
created_at: ""
author: ""
owner: ""
keywords: []
aliases: []
context: ""
sensitivity: internal
classification: business_internal
realm_label: ""
uid: ""
canonical_ref: ""
template_key: master-template
---

# {{name}}


## Notes #notes

_Context and general notes..._

```

---

## tags.folder-overlay.template.json

```text
{
  "schema_version": "2.0",
  "name": "Folder Tag Overlay Template",
  "description": "Optional folder-level tags.json. Applies only to this folder and descendants. It extends the global QiLabs tag registry without replacing it.",
  "scope": "folder",
  "registry_type": "overlay",
  "applies_to": "./",
  "inherits": "global",
  "tag_policy": {
    "allow_new_tags_within_overlay": true,
    "minimum_tags_per_note": 3,
    "max_bonus": 2,
    "always_include": [],
    "instructions": [
      "Add only tags that are genuinely specific to this folder/project/case/client/domain.",
      "Do not duplicate broad global tags unless they are folder defaults.",
      "Keep overlay tags namespaced.",
      "If an overlay tag becomes useful everywhere, promote it to the global registry later."
    ]
  },
  "allowed_tags": {
    "project": [
      "project/example"
    ],
    "people": [],
    "organizations": [],
    "case": [],
    "exhibits": [],
    "custom": []
  },
  "folder_defaults": {
    ".": [
      "#project/example"
    ]
  },
  "keyword_suggestions": {},
  "llm_output_format": {
    "required_json_output": {
      "tags": [],
      "confidence": "low | medium | high",
      "rationale": "",
      "needs_review": true,
      "unknown_tags": [],
      "source_registry": "mixed"
    }
  }
}
```
