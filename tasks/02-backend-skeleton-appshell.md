# Increment 2 — Backend skeleton + Frontend AppShell/RBAC

**Status:** done

## Scope
FastAPI app, DB models/migrations, JWT auth, permission map from §12 as data,
seed script. Frontend AppShell, routing, RBAC gate, role switcher.

## Backend deliverables
- `app/core/config.py` (pydantic-settings), `app/core/db.py` (SQLAlchemy engine/session)
- `app/core/security.py` — JWT (python-jose) + password hashing (bcrypt directly, NOT
  passlib — see gotcha below) + `get_current_user` dependency
- `app/core/permissions.py` — full §12 RBAC matrix as data (16 modules × 8 roles),
  `require_permission(module, action)` dependency, action levels F/W/R/A/-
- `app/core/audit.py` — sha256 hash-chained `record_audit_event()`, the only sanctioned
  way to write an `AuditEvent` row
- `app/models/` — core spine: Department, User (+RoleName enum), Customer, Request (+
  Channel/RequestStatus/Priority enums), Message, Attachment, Decision (+DecisionType),
  Evidence, RuleEvaluation, Feedback, AuditEvent
- `app/auth/router.py` (`POST /v1/auth/login`, `GET /v1/auth/me`), `app/admin/router.py`
  (`GET /v1/admin/departments`)
- `app/main.py` — uniform error shape `{code, message, field_errors, trace_id}` via
  exception handler, CORS for localhost:5173, `/v1/openapi.json`
- Alembic migration `44ee7bc224b8` — all 12 core-spine tables
- `backend/seed/seed.py` — 8 Nordbank departments + 7 users (one per role), password
  `arip-dev-password` for all
- `backend/tests/` — 14 pytest tests (auth success/failure, RBAC matrix spot-checks,
  endpoint-level 200/403 checks) using an in-memory SQLite fixture

## Frontend deliverables
- `src/lib/api.ts` (fetch wrapper, `ApiError`), `src/lib/auth.tsx` (AuthProvider/useAuth,
  token in localStorage), `src/lib/rbac.ts` (client-side §12 mirror — convenience only),
  `src/lib/usePermission.ts`
- `src/design-system/primitives/PermissionGate.tsx` — AccessDenied EmptyState variant
- `src/app/AppShell.tsx` (sidebar from §02 nav groups, topbar, demo-account role
  switcher), `src/app/router.tsx` (TanStack Router, code-based, routes for full §02
  sitemap as placeholders), `src/app/LoginPage.tsx`, `src/app/demoAccounts.ts`,
  `src/app/ModulePlaceholder.tsx`

## Verification
- Backend: 14/14 pytest passing; manual curl smoke test (login → /me → RBAC 403/200)
- Frontend: `tsc -b` clean, 26/26 vitest passing, prod build 128KB gzip
- **Live browser verification (Chrome via claude-in-chrome):** login as Super Admin →
  full nav visible; switched to Priya Raman (support_agent) → Business Rules correctly
  shows "Access denied", Requests correctly accessible

## Gotchas hit (see memory files for full detail)
- `conda run -n arip` was silently falling back to base env all session — arip was an
  empty shell, had to `conda install -n arip python=3.11` + reinstall every dep for real
- passlib+bcrypt5 incompatible (`AttributeError: module 'bcrypt' has no attribute
  '__about__'`) — switched to calling the `bcrypt` package directly
- Port 5432 was taken by a native Windows postgres.exe (not Docker) — moved to 5434;
  6379 taken by another project's redis container — moved to 6380
