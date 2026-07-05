# ── QiLabs Justfile ──────────────────────────────────────────────────
# Requires: https://just.systems  (install: scoop install just)
# Usage:    just <target>
# -----------------------------------------------------------------

# Default: list available commands
default:
    @just --list

# ── SETUP ─────────────────────────────────────────────────────────────
# Verify deps, install, create local data folders, print URLs
setup:
    @echo "=== QiLabs Setup ==="
    @echo "Checking required tools..."
    node --version
    pnpm --version
    python --version
    @echo "Installing JS dependencies..."
    pnpm install
    @echo "Creating local data directories..."
    -mkdir C:\QiData\inbox
    -mkdir C:\QiData\staging
    -mkdir C:\QiData\reviewed
    -mkdir C:\QiData\failed
    -mkdir C:\QiData\manifests
    -mkdir C:\QiData\logs
    -mkdir C:\QiData\extracted_text
    -mkdir C:\QiData\embeddings_cache
    @echo ""
    @echo "=== Setup complete ==="
    @echo "Next: just dev"

# ── DEV ───────────────────────────────────────────────────────────────
# Run all workspace dev servers in parallel
dev:
    @echo "=== Starting QiLabs Dev ==="
    pnpm -r run dev

# Run only QiApps
dev-apps:
    @echo "=== Starting QiApps ==="
    pnpm --filter "../60_QiApps/**" run dev

# Run only QiSites
dev-sites:
    @echo "=== Starting QiSites ==="
    pnpm --filter "../70_QiSites/**" run dev

# Run QiWorkers (Cloudflare Workers via wrangler)
dev-workers:
    @echo "=== Starting QiWorkers ==="
    pnpm --filter "../25_QiWorkers" run dev

# ── STATUS ────────────────────────────────────────────────────────────
# Check data dirs and environment
status:
    @echo "=== QiLabs Status ==="
    @echo "Checking data directories..."
    @if exist C:\QiData\inbox (echo "[OK]  C:/QiData/inbox") else (echo "[MISSING] C:/QiData/inbox — run: just setup")
    @if exist C:\QiData\staging (echo "[OK]  C:/QiData/staging") else (echo "[MISSING] C:/QiData/staging")
    @if exist C:\QiData\reviewed (echo "[OK]  C:/QiData/reviewed") else (echo "[MISSING] C:/QiData/reviewed")
    @if exist C:\QiData\failed (echo "[OK]  C:/QiData/failed") else (echo "[MISSING] C:/QiData/failed")
    @echo ""
    @echo "Done. Check .env for SUPABASE, R2, and OPENAI credentials."

# ── RESET ─────────────────────────────────────────────────────────────
# Clear local staging/log state — does NOT affect DB or cloud storage
reset:
    @echo "=== Resetting local data (does NOT touch DB) ==="
    -del /Q C:\QiData\staging\*
    -del /Q C:\QiData\logs\*
    @echo "Local staging and logs cleared."
    @echo "Run: just setup to re-create if needed."

# ── BUILD ─────────────────────────────────────────────────────────────
# Build all packages
build:
    pnpm -r run build

# Build only QiApps
build-apps:
    pnpm --filter "../60_QiApps/**" run build

# Build only QiSites
build-sites:
    pnpm --filter "../70_QiSites/**" run build

# ── LINT / TYPECHECK ──────────────────────────────────────────────────
lint:
    pnpm -r run lint

typecheck:
    pnpm -r run typecheck
