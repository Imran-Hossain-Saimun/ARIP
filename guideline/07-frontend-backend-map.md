# Frontend ↔ Backend Map

Covers: `frontend/src/app/router.tsx`, `frontend/src/lib/{api,auth,rbac}.ts`, every
`frontend/src/features/*/api.ts`.

## 1. Route → page → permission → backing API

Built from `NAV_GROUPS` in `frontend/src/lib/rbac.ts:85-110`; each nav item becomes a
child route of `appLayoutRoute` (`frontend/src/app/router.tsx:112-122`), rendering the
matching entry in `REAL_PAGES` (`:44-110`) or falling back to `ModulePlaceholder`.

| Route | Page component | Permission module | Backing `api.ts` |
|---|---|---|---|
| `/` | *(placeholder)* | `dashboard` | none yet |
| `/requests` | `RequestQueuePage` | `requests` | `features/requests/api.ts` (+ `features/decisions/api.ts` inside the trace drawer) |
| `/email` | `EmailPage` | `email` | `features/email/api.ts` |
| `/ai` | `AiPipelineMonitorPage` | `decision_trace` | `features/ai/api.ts` |
| `/knowledge` | `KnowledgeLibraryPage` | `knowledge_authoring` | `features/knowledge/api.ts` (+ `features/reference/api.ts` for dept lookups) |
| `/knowledge/gaps` | `KnowledgeGapsPage` | `knowledge_authoring` | `features/knowledge/api.ts` |
| `/workflows` | `WorkflowsPage` | `workflow_builder` | `features/automation/api.ts` |
| `/routing` | `RoutingPage` | `routing_config` | `features/automation/api.ts` |
| `/rules` | `BusinessRulesPage` | `business_rules` | `features/automation/api.ts` |
| `/prompts` | `PromptsPage` | `prompt_management` | `features/automation/api.ts` |
| `/analytics` | `AnalyticsPage` | `analytics` | `features/analytics/api.ts` |
| `/audit` | `AuditLogPage` | `audit_logs` | `features/audit/api.ts` |
| `/admin` | `AdminPage` | `admin_users` | `features/admin/api.ts` (+ `features/reference/api.ts`) |
| `/settings` | `SettingsPage` | `integrations` | `features/settings/api.ts` |
| `/portal` | `SubmitPage` | *(none — outside RBAC entirely)* | `features/portal/api.ts` |
| `/portal/track` | `TrackPage` | *(none)* | `features/portal/api.ts` |
| `/login` | `LoginPage` | *(none)* | `lib/auth.tsx` → `POST /v1/auth/login` |

Workflows/Routing/Business Rules/Prompts all share one `features/automation/api.ts`,
mirroring the backend's single `ConfigResource` implementation (see
[05-automation-versioned-config.md](05-automation-versioned-config.md)).

## 2. Every feature's `api.ts` — exported function → HTTP call

**`requests`**: `listRequests` → `GET /v1/requests`; `getRequest` → `GET /v1/requests/{id}`;
`assignRequest` → `PATCH /v1/requests/{id}/assign`; `approveRequest` → `POST
/v1/requests/{id}/approve` (fresh Idempotency-Key); `escalateRequest` → `POST
/v1/requests/{id}/escalate` (Idempotency-Key).

**`decisions`**: `getDecisionTrace` → `GET /v1/decisions/{id}/trace`; `replayDecision` →
`POST /v1/decisions/{id}/replay` (Idempotency-Key) — hits the stub, see
[01-request-lifecycle.md](01-request-lifecycle.md) §4.

**`knowledge`**: `listKnowledge` → `GET /v1/knowledge`; `getKnowledgeArticle` → `GET
/v1/knowledge/{id}`; `ingestKnowledge` → `POST /v1/knowledge/ingest` (multipart);
`approveKnowledgeVersion` → `POST /v1/knowledge/{id}/versions/{version}/approve`;
`listKnowledgeGaps` → `GET /v1/gaps`.

**`email`**: `listMailboxes` → `GET /v1/email/mailboxes`; `syncMailbox` → `POST
/v1/email/mailboxes/{id}/sync`; `listParseFailures` → `GET /v1/email/parse-failures`;
`resolveParseFailure` → `POST /v1/email/parse-failures/{id}/resolve`.

**`automation`**: `listCurrent` → `GET /v1/automation/{kind}`; `listVersions` → `GET
/v1/automation/{kind}/{key}/versions`; `createDraft` → `POST /v1/automation/{kind}`;
`publishResource` → `POST /v1/automation/{id}/publish`; `rollbackResource` → `POST
/v1/automation/{kind}/{key}/rollback/{version}`; `simulateRule` → `POST
/v1/rules/simulate`; `listWorkflowRuns` → `GET /v1/workflows/runs`;
`retryWorkflowAction` → `POST /v1/workflows/runs/{runId}/actions/{actionId}/retry`.

**`analytics`**: `getKpis` → `GET /v1/analytics/kpis?range={days}`.

**`audit`**: `listAuditEvents` → `GET /v1/audit`; `verifyChain` → `GET /v1/audit/verify`.

**`admin`**: `listUsers` → `GET /v1/admin/users`; `createUser` → `POST /v1/admin/users`;
`updateUser` → `PATCH /v1/admin/users/{id}`; `createDepartment` → `POST
/v1/admin/departments`.

**`settings`**: `listSettings` → `GET /v1/settings`; `updateSetting` → `PUT
/v1/settings/{key}`.

**`ai`**: `runPipeline` → `POST /v1/ai/run`.

**`portal`**: `submitPortalRequest` → `POST /v1/portal/requests`; `trackPortalRequest` →
`GET /v1/portal/requests/{reference}?email=...`; `submitPortalFeedback` → `POST
/v1/portal/requests/{reference}/feedback`.

**`reference`** (shared lookup, used by `admin` and `knowledge`): `listDepartments` →
`GET /v1/departments`.

## 3. How `api.ts` resolves URLs and auth

`frontend/src/lib/api.ts`:
- `API_URL` read once from `import.meta.env.VITE_API_URL` (`:1`) — set in `frontend/.env`
  to `http://localhost:8010`. **The backend dev server must bind port 8010**, not 8000 —
  a mismatch here produces silent-looking 503s with no useful frontend error.
- Full URL is built by string concatenation: `` `${API_URL}${path}` `` (`:32`) — every
  call site's path must start with `/`.
- A module-level `authToken` variable (`:25`) is armed via `setAuthToken(token)` (`:27-29`,
  called from `lib/auth.tsx`). Every request conditionally attaches `Authorization:
  Bearer {authToken}` — purely an in-memory bearer token, no cookies.
- `Content-Type: application/json` is only added when a body is present; multipart
  uploads (`requestForm()`) omit it so the browser sets the boundary itself.
- Non-OK responses parse into `ApiErrorBody {code, message, field_errors, trace_id}` and
  throw `ApiError`, falling back to `response.statusText` if the body isn't JSON. `204` →
  `undefined`.

## 4. Login flow end to end

1. `LoginPage` calls `useAuth().login(email, password)`.
2. `auth.tsx` calls `api.post('/v1/auth/login', {email, password})` →
   `{access_token}`.
3. Token persisted to `localStorage` under `arip.token` (`TOKEN_STORAGE_KEY`).
4. `hydrate(token)` arms `setAuthToken(token)` in `lib/api.ts`, then fetches the current
   user via `GET /v1/auth/me`, storing it in React state.
5. On app reload, `AuthProvider`'s effect reads the token back from `localStorage` and
   re-hydrates — if `/v1/auth/me` fails, the stored token is cleared.
6. `logout()` clears `localStorage`, the in-memory token, and user state.
7. Route guarding is inline in `AppShell`, not the router config:
   `if (!user) return <Navigate to="/login" />` — the router explicitly notes "AppShell
   itself redirects to /login when unauthenticated... the route tree doesn't need a
   separate guard component" (`router.tsx:31-32`).
8. A dev-only "switch demo account" affordance in `AppShell.tsx` calls `login(email,
   'arip-dev-password')` against a static `DEMO_ACCOUNTS` list for quick role switching —
   see `backend/seed/seed.py` for the actual seeded accounts/roles.

## 5. Portal routes genuinely bypass AppShell/login

`router.tsx:124-127` builds `/portal` as a **separate route tree**, parented directly on
`rootRoute`, not on `appLayoutRoute`:
```javascript
// Customer portal is a separate route tree — no login, no AppShell/sidebar.
const portalLayoutRoute = createRoute({ getParentRoute: () => rootRoute, path: '/portal', component: PortalLayout })
```
`routeTree` adds `portalLayoutRoute.addChildren([...])` as a sibling of
`appLayoutRoute.addChildren(moduleRoutes)` — never nested under it, so `PortalLayout`
never passes through `AppShell`'s auth guard. `PortalLayout` has its own standalone
header/nav with no `useAuth()` call at all — consistent with the backend's `/v1/portal/*`
endpoints being genuinely public (see
[01-request-lifecycle.md](01-request-lifecycle.md) §7).
