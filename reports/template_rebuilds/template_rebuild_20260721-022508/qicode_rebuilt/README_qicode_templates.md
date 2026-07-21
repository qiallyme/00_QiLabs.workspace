# QiCode Template Set

These templates support the QiCode law-book structure.

## Canonical Structure

```text
Title folder
├── _index.md
├── title_##_slug.md
├── article_01_slug.md
├── article_02_slug.md
└── article_03_slug.md
```

Sections stay inside article files. Do not create section files.

## Numbering

| Level | Human Code | Stable ID |
|---|---|---|
| Title | `§ TT.00.000` | `T##` |
| Article | `§ TT.AA.000` | `T##.A##` |
| Section | `§ TT.AA.SSS` | `T##.A##.S###` |
| Line | `§ TT.AA.SSS.LLL` | `T##.A##.S###.L###` |

Example:

```text
Title 07 Ethics              = § 07.00.000
Article 02 Responsibility    = § 07.02.000
Section 100 First Section    = § 07.02.100
Line 001                     = § 07.02.100.001
```

## File Naming

Use snake_case filenames and kebab-case slugs.
