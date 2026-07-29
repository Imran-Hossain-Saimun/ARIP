# Increment 6 — Email inbox, mailbox config, parse-failure triage

**Status:** done (backend fully verified incl. real SMTP send; frontend build/test-clean
but NOT click-verified live in a browser this pass — same tooling issue as increment 5)

## Scope
Mailhog stands in for real IMAP/Graph for local dev — already running in
`docker-compose.yml` (SMTP :1026, web UI/API :8025 — see port note below).

## Backend
- `app/email/` — mailbox connection config, IMAP IDLE-style polling (or Mailhog's HTTP
  API for dev), MIME parsing, thread correlation (§07 sequence diagram: mail server →
  email engine → Redis queue → Intake Service)
- Normalize/dedupe/spam-check/PII-mask pipeline stage (FR-014/016) feeding into the same
  Request creation path as increment 3's web channel
- Parse-failure queue: malformed MIME, unsupported attachments, etc. land here for triage
  rather than silently dropping

## Frontend
- Unified inbox (3 mailboxes per the prototype), thread view, mailbox connection config
  screen, parse-failure triage queue

## Verification target
- Send a test email via Mailhog's SMTP → confirm it becomes a `Request` with `channel =
  email`, correctly threaded to prior messages on reply
- A deliberately malformed message lands in the parse-failure queue, not silently lost

## Delivered
- Backend: `Mailbox`/`ParseFailure` models (migration `13f27fc685a3`). `app/email/`:
  `mailhog_client.py` (Mailhog's HTTP API already parses MIME for us — no raw parsing
  needed for this provider), `sync.py` (`sync_mailbox`: filters Mailhog's shared message
  pool by `to_addresses` so multiple `Mailbox` rows stay logically separate, thread-
  correlates replies by a `REQ-XXXX` reference regex match against the subject, else
  creates a new `Request` on the same spine as the web/increment-3 path, and turns
  anything malformed — missing/invalid From, empty subject+body — into a `ParseFailure`
  row instead of raising or silently dropping it). New endpoints: `GET/POST
  /v1/email/mailboxes`, `POST /v1/email/mailboxes/:id/sync`, `GET /v1/email/parse-
  failures`, `POST /v1/email/parse-failures/:id/resolve`. Added a `channel` filter to the
  existing `GET /v1/requests` (increment 3) so the "unified inbox" is just that endpoint
  filtered to `channel=email` — no parallel inbox data model. 7 new pytest tests (54
  total), **two of which are real end-to-end**: they send an actual email via `smtplib`
  to the dockerized Mailhog, hit the real `/sync` endpoint, and assert a `Request` was
  created / an existing one was threaded — this is the strongest verification any
  increment has gotten so far, since it exercises the full send→receive→parse→persist
  path with no mocks.
- Seed script now creates 2 real `Mailbox` rows (Retail Banking, Cards & Payments).
- Frontend: `features/email/{types,api,EmailInboxTab,MailboxesTab,EmailPage}.tsx`. The
  inbox tab reuses `RequestList`/`RequestRecord` verbatim (filtered to `channel=email`)
  rather than building parallel components — matches the backend's "no parallel data
  model" decision.
- **A real port-conflict bug found and fixed along the way**: Mailhog's SMTP port 1025
  was silently claimed by an unrelated native Windows service. Unlike the earlier
  Postgres/Redis port conflicts (which failed loudly), this one let TCP connections
  *succeed* and then just never sent an SMTP greeting — `smtplib` hung forever (no
  default timeout) instead of erroring. Diagnosed via `docker compose logs mailhog`
  showing zero incoming-connection lines while a client believed it was connected.
  Mailhog's SMTP now maps to host port **1026** instead (see `[[docker-port-conflicts]]`
  memory). Also fixed: `smtplib.SMTP(...)` in the test helper now always passes an
  explicit `timeout=`, so a future conflict like this fails fast instead of hanging.
- **Simplification not in the original plan**: no PII-masking or spam-detection stage —
  inbound messages are normalized (from/subject/body extracted) and deduped only via the
  reference-number thread match; a dedicated PII-mask/spam-check pass (FR-016) isn't
  implemented.
- **Known gap this pass**: same as increment 5 — frontend not click-verified live in a
  browser (claude-in-chrome tooling issue, reproduced twice now: `form_input` sets a
  field's value but a subsequent click doesn't register as a real interaction). Backend
  confidence is unusually high here given the real-SMTP tests; the frontend risk surface
  is limited to reusing already-proven `RequestList`/`RequestRecord` plus two new simple
  list screens.
