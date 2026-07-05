# QiLabs Workspace

`00_QiLabs.workspace` is the centralized orchestration layer, configuration registry, and scripting toolbox for the entire QiLabs ecosystem. All monorepo tooling, shared config, workspace manifests, and dev utilities live here.

## Repository Map

| Folder | Project | Description |
| :--- | :--- | :--- |
| [`10_QiSpark`](c:/QiLabs/10_QiSpark) | **QiSpark** | Static site builder and snapshot pipeline |
| [`20_QiServer`](c:/QiLabs/20_QiServer) | **QiServer** | Supabase database, API schemas, fleet/flows/memory layers |
| [`25_QiWorkers`](c:/QiLabs/25_QiWorkers) | **QiWorkers** | Cloudflare Workers — ingestion, embedding, graph, semantic routing |
| [`30_QiDrive`](c:/QiLabs/30_QiDrive) | **QiDrive** | Local file/data drive layer |
| [`40_QiVault`](c:/QiLabs/40_QiVault) | **QiVault** | Personal knowledge base (Obsidian vault) |
| [`60_QiApps`](c:/QiLabs/60_QiApps) | **QiApps** | App suite — QiLife, QiLegal, QiCare, QiFi, QiTrials |
| [`70_QiSites`](c:/QiLabs/70_QiSites) | **QiSites** | Public web properties — QiAlly.com, QSaysIt.com, QiLuma |

## Workspace Structure

```
00_QiLabs.workspace/
├── _qiconfig/          # Shared config, agent rules, tags, schema templates
├── 20_manifests/       # Workspace root manifests
├── 90_audits/          # Structural audits and historical diagrams
├── toolbox/            # QiLabs Toolbox — local Python GUI utility
├── .github/            # CI/CD workflows, PR templates, CODEOWNERS
├── justfile            # Task runner (install: scoop install just)
├── package.json        # Workspace-level scripts and shared dependencies
├── pnpm-workspace.yaml # pnpm monorepo package boundaries
└── .env.example        # Environment variable template
```

## Quick Start

```bash
# Install dependencies
pnpm install

# Run all dev servers
just dev

# Check workspace status
just status

# Run linting
just lint
```

## Environment

Copy `.env.example` to `.env` and fill in credentials for:
- **Supabase** — database and auth
- **Cloudflare R2** — file storage
- **Resend** — transactional email
- **OpenAI** — embeddings

See `.env.example` for all required variables.
