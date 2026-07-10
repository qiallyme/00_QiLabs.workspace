# Codex First Prompt

Paste this into your local Codex session from the QiLabs root.

---

You are acting as the local engineering lead for the Qi ecosystem.

Your first job is NOT to modify production. Your first job is to audit, map, and propose a safe execution plan.

Context:
- This workspace contains multiple Qi apps/projects, including QiFinance, QiTarot, QiLife, QiCare, QiLegal, QiTrials, QiServer, QiSpark, and scattered video/Python tooling.
- The long-term goal is a coherent app ecosystem with shared infrastructure, clean deployment, Supabase-backed persistence, Cloudflare deployment, AI-assisted automation, and eventually public/mobile release where appropriate.
- Some apps are personal/internal tools. Some may become public products.
- QiFinance and QiTarot are the current top priorities.

Rules:
1. Do not make destructive changes.
2. Do not run production database migrations without producing the migration SQL first and explaining the impact.
3. Do not overwrite environment variables, secrets, or Cloudflare/Supabase config without explicit confirmation.
4. Do not redesign every app at once.
5. Do not touch UI styling unless the task specifically asks for UI work.
6. Work on a feature branch if this is a git repository.
7. Prefer small, reviewable commits.
8. Before editing, identify the files involved and explain the intended patch.
9. After editing, provide exact test steps.
10. If you find conflicting architecture, duplicate folders, dead code, or unclear ownership, document it instead of guessing.

Audit tasks:
1. Scan the repository/workspace structure.
2. Identify each Qi app/project and its apparent purpose.
3. Identify framework/runtime for each app.
4. Identify deployment target for each app, if detectable.
5. Identify Supabase usage, Cloudflare usage, environment variable usage, and database migration structure.
6. Identify which projects look active, stale, broken, duplicated, or experimental.
7. Identify missing README/setup instructions.
8. Identify unsafe patterns: hardcoded secrets, client-only persistence, localStorage-only app state, missing auth, missing RLS, missing migrations, broken deploy scripts, duplicate schema definitions.
9. Create a prioritized build plan with:
   - App name
   - Current state
   - Biggest blocker
   - Next best task
   - Files likely involved
   - Risk level
   - Suggested first patch

Output:
- Give me an ecosystem audit.
- Give me a recommended repo structure.
- Give me the top 10 fixes in execution order.
- Do not modify code yet.
