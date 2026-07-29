# ARIP — Project Notes for Claude

AI Request Intelligence Platform for a fictional bank ("Nordbank"): customer request
intake (web portal + email) → hybrid RAG retrieval → confidence-scored AI decision →
business-rule override → auto-reply/draft/clarify/route → audit trail. Built from the
design spec at `project/ARIP Design.dc.html` (14 modules, 46 screens, 90 FRs, 8 roles).

**Start here:**
- `guideline/00-setup.md` — local setup from a clean clone (infra, backend, frontend,
  migrations, seed data, running tests), every command verified.
- `guideline/README.md` — how the app actually works, module by module, with exact
  `file:line` code citations. Read the relevant `guideline/0N-*.md` before answering "how
  does X work" questions instead of re-deriving from scratch.
- `tasks/README.md` — build history/changelog, one file per increment (all 9 delivered,
  plus a post-build increment 10 for OpenRouter support).
- `C:\Users\saimun\.claude\plans\wise-hugging-scott.md` — the original architecture plan
  (repo layout, data model, API surface, 9-increment build order). Historical context,
  not a live doc.

## Stack

FastAPI (modular monolith, `app/<domain>/` router modules) + SQLAlchemy 2.0 + Alembic +
Postgres 16/pgvector + Redis + MinIO + Mailhog, JWT auth. React 19 + TypeScript + Vite +
Tailwind v4 + TanStack Query/Router/Table.

## Environment gotchas

- **Backend dev server MUST bind port 8010**, not 8000 — `frontend/.env`'s
  `VITE_API_URL` hardcodes `http://localhost:8010`. Starting on 8000 gives silent-looking
  503s on every frontend API call.
- Docker Compose port remaps (host already runs other projects' containers + native
  Windows services on common ports): Postgres **5434**, Redis **6380**, Mailhog SMTP
  **1026**.
- npm/npx `.cmd` shims break because the path contains "R&D" (`&` is a cmd.exe command
  separator) — invoke Node entrypoints directly, e.g.
  `node ./node_modules/typescript/bin/tsc -b`, `node ./node_modules/vitest/vitest.mjs run`.
- Dev seed password for every seeded user: `arip-dev-password`
  (`backend/seed/seed.py` has the 7 accounts/roles/emails).
- LLM providers are pluggable and zero-config by default: `ANTHROPIC_API_KEY` →
  `OPENROUTER_API_KEY` → heuristic keyword fallback for chat/classification;
  `OPENAI_API_KEY` → deterministic hash fallback for embeddings. **OpenRouter has no
  embeddings endpoint** — it can't upgrade retrieval quality, only classification.

## Known real gaps (not oversights — see `guideline/README.md` for the full list)

- Email ingestion (Mailhog polling) is **never connected to the AI pipeline** — no
  automatic classification/decision for email-sourced requests, and no real IMAP/OAuth or
  outbound SMTP send exists anywhere in `app/`.
- `POST /v1/decisions/{id}/replay` is a stub (validates existence only).
- `WorkflowRun`/`WorkflowAction` have no live execution engine.
- Idempotency-Key dedup is in-process with no TTL — single API instance only.
- Realtime `/v1/stream` is 2s polling with a ~2min connection cap, not real push.

## Git

Remote: `git@github.com:Imran-Hossain-Saimun/ARIP.git`, branch `master`. Root
`.gitignore` excludes `.env`, `__pycache__`, `.claude/`, `node_modules`, `dist` — never
commit `.env` (use `.env.example` as the template).
