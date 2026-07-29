# ARIP — AI Request Intelligence Platform

AI request orchestration for a fictional bank ("Nordbank"): customer intake (web portal +
email) → hybrid RAG retrieval → confidence-scored AI decision → business-rule override →
auto-reply/draft/clarify/route → audit trail.

FastAPI (modular monolith) + SQLAlchemy 2.0 + Alembic + Postgres/pgvector + Redis + MinIO
+ Mailhog backend. React 19 + TypeScript + Vite + Tailwind v4 + TanStack Query/Router/
Table frontend.

## Getting started

See [`guideline/00-setup.md`](guideline/00-setup.md) for local setup from a clean clone —
infra, backend, frontend, migrations, seed data, running tests.

## Documentation

- [`guideline/`](guideline/README.md) — how the app actually works: request lifecycle,
  knowledge/retrieval, the AI pipeline, email processing, automation, RBAC/audit, and the
  frontend-to-backend map, all with exact `file:line` code references.
- [`tasks/`](tasks/README.md) — build history, one file per delivery increment.
- `project/ARIP Design.dc.html` — the original design spec this was built from.

## Repo layout

```
backend/    FastAPI app (app/<domain>/ router modules), Alembic migrations, seed data
frontend/   React app (src/features/<domain>/), design system, TanStack Router
guideline/  How the app works, with code references
tasks/      Build history/changelog
project/    Original design spec
```
