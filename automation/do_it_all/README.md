# QiLabs Do-It-All

This adds one guarded workspace-wide pipeline.

## Install

Extract the bundle directly into:

`C:\QiLabs`

That should create:

- `C:\QiLabs\DO_IT_ALL.bat`
- `C:\QiLabs\DO_IT_ALL_DRY_RUN.bat`
- `C:\QiLabs\00_QiLabs.workspace\automation\do_it_all\Invoke-QiLabsDoItAll.ps1`
- `C:\QiLabs\00_QiLabs.workspace\automation\do_it_all\qilabs.do-it-all.config.json`

Run `DO_IT_ALL_DRY_RUN.bat` first. Then use `DO_IT_ALL.bat`.

## Pipeline order

1. Removes only allowlisted cache and log bloat.
2. Optionally invokes configured housekeeping hooks.
3. Finds Node project roots.
4. Synchronizes dependencies to existing lockfiles.
5. Runs each project's `build` script when present.
6. Finds every Git repository recursively.
7. Processes the most deeply nested repositories first.
8. Blocks commits containing secret-like or database files.
9. Commits workspace changes.
10. Fetches, rebases, pushes, and runs Git maintenance.
11. Continues past individual project failures and writes a final audit.

## Important housekeeping hook

The configuration includes a disabled hook for:

`housekeeping_console.py --apply-all --non-interactive`

Enable it only after the housekeeping console actually supports those flags. Do not point this pipeline at an interactive GUI launcher, or the one-click run will stall.

Edit:

`00_QiLabs.workspace\automation\do_it_all\qilabs.do-it-all.config.json`

Change:

```json
"enabled": false
```

to:

```json
"enabled": true
```

after the noninteractive command exists.

## Safety rules

The pipeline does not:

- force-push
- delete source folders
- delete `node_modules`
- upgrade dependency versions
- publish secret-like files
- continue a conflicted rebase

Dependency synchronization means restoring the versions already specified by each lockfile. Package upgrades should be a separate reviewed process.

## Logs

Every run writes a text log and JSON summary under:

`C:\QiLabs\00_QiLabs.workspace\90_audits\do_it_all`


## Scan boundaries

Every phase now excludes these roots by default:

- `30_QiDrive`
- `90_QiArchive`

It also ignores directory copies named `legacy`, `backup`, `backups`,
`backups_before_frontmatter`, and `.Encrypted`.

These exclusions apply to:

- bloat cleanup
- Node project discovery
- Git repository discovery

This prevents the pipeline from operating on synchronized drive mirrors,
archived workspace copies, and stale backup repositories.

Adjust the `scope` section in `qilabs.do-it-all.config.json` when the canonical
QiLabs root names change.


## v4 compatibility fix

Optional `package.json` fields such as `workspaces`, `packageManager`, and
`scripts` are now read safely under PowerShell strict mode. Projects are not
required to define those fields.

The JSON audit writer also explicitly enumerates result collections for
Windows PowerShell 5.1 compatibility.
