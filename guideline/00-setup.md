# Local Setup

How to get ARIP running from a clean clone. Every command below was actually run and
verified while writing this doc — not copied from a template. If a step fails for you in
a way not covered here, check `CLAUDE.md` and this repo's memory notes for known
environment gotchas before assuming the app is broken.

## Prerequisites

- Docker Desktop (Postgres/Redis/MinIO/Mailhog all run as containers — nothing to install
  natively)
- Python 3.11+ (`requires-python = ">=3.11"`, `backend/pyproject.toml:5`)
- Node.js 20+ (tested with Node 24)
- A shell that isn't cmd.exe if your path contains `&` — see the Windows note at the
  bottom.

## 1. Start infrastructure

```bash
docker compose up -d
```

This starts four containers, defined in `docker-compose.yml` (remapped from their
default ports because this host runs other projects/native services on the usual ones):

| Service | Image | Host port | Purpose |
|---|---|---|---|
| postgres | `pgvector/pgvector:pg16` | **5434** → 5432 | Primary DB + pgvector |
| redis | `redis:7-alpine` | **6380** → 6379 | Cache/broker (Celery not actually wired up yet) |
| minio | `minio/minio:latest` | 9000 (API), 9001 (console) | S3-compatible object storage |
| mailhog | `mailhog/mailhog:latest` | **1026** → 1025 (SMTP), 8025 (web UI + API) | Fake inbox for local email dev |

Confirm everything is healthy before continuing:
```bash
docker compose ps
```
All four should show `Up`/`healthy`. If a container won't bind its port, something else
on the host already owns it — see `CLAUDE.md`'s port-remap note; don't just change the
port here without also updating `backend/.env`, since several values are cross-referenced.

## 2. Backend

### 2a. Python environment

Any of these work — pick one:

**venv (most portable):**
```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate   # Windows Git Bash; use .venv/bin/activate on macOS/Linux
```

**conda** (how this repo's dev environment was actually built):
```bash
conda create -n arip python=3.11
conda activate arip
```
If you're on Windows using conda from a Git Bash shell, `conda activate`/`conda run -n
arip` can silently fall back to the base environment without erroring. Verify with:
```bash
conda run -n arip python -c "import sys; print(sys.executable)"
```
and confirm the printed path is actually under `envs\arip`, not the base env's path. If
it isn't, invoke the env's `python.exe`/`pip.exe` by their full path instead of relying on
`conda run`/`conda activate`.

### 2b. Install dependencies

```bash
pip install -e ".[dev]"
```
Installs everything listed in `backend/pyproject.toml:6-26` (runtime deps + the `dev`
extra: pytest, pytest-mock, httpx, ruff) in one shot, editable so code changes take
effect without reinstalling. This relies on `[tool.setuptools] packages = ["app"]`
(`pyproject.toml:28-29`) — without it, setuptools' automatic package discovery finds
multiple top-level directories that look like packages (`app`, `alembic`, `seed`,
`tests`) and refuses to guess which one is the distribution root
(`error: Multiple top-level packages discovered in a flat-layout`). If you ever see that
error, it means this line was removed from `pyproject.toml`.

### 2c. Configure environment

```bash
cp .env.example .env
```
Defaults in `.env.example` already match the docker-compose ports above (`DATABASE_URL`
→ 5434, `REDIS_URL` → 6380, `SMTP_PORT` → 1026) and MinIO's default credentials — no
edits needed to run locally. `ANTHROPIC_API_KEY`/`OPENAI_API_KEY`/`OPENROUTER_API_KEY`
are all optional; leave them blank to run entirely on the zero-config heuristic/
deterministic-hash fallbacks (see
[03-ai-pipeline-and-llm-providers.md](03-ai-pipeline-and-llm-providers.md)).

### 2d. Run migrations

```bash
alembic upgrade head
```
`alembic/env.py:8,15` reads `DATABASE_URL` out of `Settings` (i.e., your `.env`) rather
than the placeholder in `alembic.ini` — so this only works once `.env` exists.

### 2e. Seed demo data (optional but recommended)

```bash
python -m seed.seed
```
Run from inside `backend/` (this is a namespace-package invocation, not a script path —
running `python seed/seed.py` directly will fail on the `from app...` imports). Creates 8
departments, 7 Nordbank demo users (all sharing password `arip-dev-password`), ~16 sample
requests with decisions/evidence, knowledge articles, mailboxes, and automation resources.
Safe to skip if you'd rather start from an empty DB — the app runs either way.

### 2f. Run the backend

```bash
uvicorn app.main:app --reload --port 8010
```
**Must bind port 8010, not the uvicorn default of 8000.** `frontend/.env`'s
`VITE_API_URL` hardcodes `http://localhost:8010` — starting on 8000 doesn't error, it
just gives every frontend API call a silent-looking failure with no useful message.

Confirm it's up:
```bash
curl http://127.0.0.1:8010/v1/openapi.json
```

### 2g. Run backend tests

```bash
pytest
```
Uses an in-memory SQLite fixture (`tests/conftest.py:13`) — **does not require Docker to
be running** for the main suite. Two exceptions in `tests/test_email.py` are marked
`@requires_mailhog` and auto-skip (not fail) if Mailhog isn't reachable on
`localhost:8025` (`test_email.py:27`) — bring `docker compose up -d mailhog` up first if
you want those to actually run.

## 3. Frontend

### 3a. Install

```bash
cd frontend
npm install
```

### 3b. Configure environment

```bash
cp .env.example .env
```
Already set to `VITE_API_URL=http://localhost:8010` — matching the backend port above.

### 3c. Run the dev server

**Don't use `npm run dev`/`npm test`/`npm run build` if your project path contains an
unescaped `&`** (as this repo's does: `R&D`). On Windows, `npm run <script>` and any
`.cmd`-shimmed binary (`vite`, `tsc`, `vitest`, ...) shell out through `cmd.exe`, which
treats a bare `&` as a command separator and either mangles the resolved path or throws
`MODULE_NOT_FOUND`. `npm install` itself is fine — this only bites when *running*
installed tools afterward. Invoke the JS entrypoint directly instead:

```bash
node ./node_modules/vite/bin/vite.js              # dev server, defaults to :5173
node ./node_modules/vite/bin/vite.js build         # production build
node ./node_modules/typescript/bin/tsc -b          # typecheck
node ./node_modules/vitest/vitest.mjs run          # test suite (single run)
```
If your path has no `&` in it, the normal `npm run dev`/`npm run build`/`npm test`
scripts (`frontend/package.json:6-13`) work exactly the same way.

Confirm it's up:
```bash
curl http://localhost:5173/
```

### 3d. Log in

Open `http://localhost:5173/login`. Any seeded account works with password
`arip-dev-password` — e.g. `super.admin@nordbank.example` for full access. See
`backend/seed/seed.py` for the other 6 accounts/roles. The customer-facing portal at
`http://localhost:5173/portal` needs no login at all.

## What you should end up with

- Backend on `http://localhost:8010`, OpenAPI docs at `/docs`.
- Frontend on `http://localhost:5173`.
- Mailhog web UI at `http://localhost:8025` (fake inbox for the email module).
- MinIO console at `http://localhost:9001` (login `arip` / `aripsecret`).

For how the app actually behaves once it's running, start at
[README.md](README.md) and the module docs it links to.
