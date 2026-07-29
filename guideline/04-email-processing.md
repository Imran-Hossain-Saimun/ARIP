# Email Processing

Covers: `backend/app/email/{mailhog_client,sync,router}.py`,
`backend/app/models/email.py`, `docker-compose.yml` (mailhog service).

**Read this doc before assuming email works like the portal does — it doesn't.** Email
ingestion is real and tested, but it is not connected to the AI pipeline, not connected
to a real mailbox, and has no outbound send capability. This is the single biggest gap
between the design spec and the implemented code.

## 1. Data model

**`MailboxProvider`** (`backend/app/models/email.py:12-15`): `MAILHOG` (the only one
actually implemented), `IMAP`, `GRAPH` (enum values exist, **no code behind them**).

**`Mailbox`** (`:24-34`): `name`, `email_address` (unique), `provider`, `department_id` FK
(SET NULL), `status` (`MailboxStatus`: `CONNECTED`/`DISCONNECTED`/`ERROR`, default
`DISCONNECTED`), `last_synced_at`.

**`ParseFailure`** (`:37-50`) — docstring: "logged instead of silently dropped." Fields:
`mailbox_id` FK CASCADE, `raw_subject`, `raw_from`, `error_message`, `raw_source` (the
full raw Mailhog JSON item), `resolved` (default `False`). **No FK to `Request`** — a
parse failure never becomes a request; it's a dead-end triage record.

## 2. How sync actually works today

**It's HTTP polling of Mailhog's REST API — not real IMAP.**

- `fetch_messages()` (`backend/app/email/mailhog_client.py:23-45`) calls
  `httpx.get(f"{MAILHOG_API_BASE}/messages", ...)` where
  `MAILHOG_API_BASE = "http://127.0.0.1:8025/api/v2"` (`:10`) is a **hardcoded literal** —
  it does not read `SMTP_HOST`/`SMTP_PORT` from `Settings` at all.
- `delete_message()` (`:48-51`) removes a processed message from Mailhog (Mailhog has no
  read/unread flag, so this is how "already processed" is tracked).
- `sync_mailbox(db, mailbox)` (`backend/app/email/sync.py:18-50`) hard-guards on
  provider: `if mailbox.provider != MailboxProvider.MAILHOG: raise NotImplementedError`
  (`:22-23`) — IMAP/Graph mailboxes cannot sync at all today.
- **Trigger: on-demand HTTP call only.** `POST /v1/email/mailboxes/{id}/sync` is the only
  trigger — there is no polling loop, cron, Celery beat task, or scheduler anywhere.
- Mailhog is a shared catch-all inbox; `sync_mailbox` filters to the target mailbox by
  checking `mailbox.email_address` against each message's `to_addresses` (`sync.py:27-28`)
  — an explicit simplification since real IMAP/Graph accounts wouldn't need this filter.
- `mailbox.last_synced_at`/`status=CONNECTED` are stamped unconditionally on every sync
  call, success or not (`sync.py:47-48`).

## 3. Thread correlation — subject-based reference matching only

Done in `_process_message()` (`backend/app/email/sync.py:53-79`).

1. Basic validation: reject (raise `ValueError`, becomes a `ParseFailure`) if the `From`
   address is missing/malformed, or if both subject and body are empty (`:54-57`).
2. **Correlation is a regex match on the subject line, not headers**:
   ```python
   REFERENCE_RE = re.compile(r"REQ-[A-Z0-9]+", re.IGNORECASE)   # :15
   ```
   If found, look up `Request.reference == ref_match.group().upper()` (`:61`) and append
   a new customer `Message` to that existing request (`:63`), record `email.threaded`.
   **There is no `Message-ID`/`In-Reply-To`/`References` header parsing anywhere** — this
   only works if the customer's mail client preserves `REQ-XXXXXXXX` in the subject when
   replying.
3. If no reference match: look up `Customer` by exact email address, create one if
   missing (full name = the email's local-part, no real name parsing, `:69`); create a
   new `Request` with `channel=EMAIL`, `status=RECEIVED`, `department_id=mailbox.
   department_id` (`:73-74`).

## 4. Parse-failure handling

Created on any `ValueError` from `_process_message` (`sync.py:30-44`), storing
`mailbox_id`, `raw_subject`, `raw_from`, `error_message`, and the full raw JSON. The
failed message is still deleted from Mailhog afterward (`sync.py:45`, unconditional) — so
**a parse failure is not retried on the next sync**, it's a one-shot record.

Triage endpoints (`backend/app/email/router.py`):
- `GET /v1/email/parse-failures` (`:56-65`, optional `?resolved=` filter)
- `POST /v1/email/parse-failures/{id}/resolve` (`:68-80`) — flips `resolved=True`. **No
  endpoint retries or converts a parse failure into a real Request** — resolution is just
  a human-looked-at-it flag.

## 5. Classification — the real gap

**`sync.py` never imports or calls `run_pipeline`.** Grep confirms `run_pipeline` is only
referenced in `ai/pipeline.py` (definition), `ai/router.py` (staff sandbox), and
`portal/router.py` (customer submit). Email-sourced requests are inserted directly with
`status=RECEIVED` and **never automatically classified** — no `Decision` row gets
created, confidence never gets scored, no business rule ever gets checked, for any
request that arrived via email. There is currently no code path (background job,
webhook, manual trigger) that runs the pipeline on an email-origin request after
ingestion.

**If you're building on this:** an agent working the queue would need to manually invoke
whatever decision-making exists, or this needs a new integration point calling
`run_pipeline` for email-sourced requests, before email traffic gets the same automation
web traffic gets.

## 6. Every endpoint (`backend/app/email/router.py`)

Prefix `/v1/email` (`:14`).

| Method + path | Line | Purpose | Permission |
|---|---|---|---|
| `GET /v1/email/mailboxes` | `:17-22` | List mailboxes | `email`/READ (`:20`) |
| `POST /v1/email/mailboxes` | `:25-35` | Create a mailbox | `email`/WRITE (`:29`) |
| `POST /v1/email/mailboxes/{id}/sync` | `:38-53` | Trigger sync now; 404 if not found, 422 `provider_not_supported` if not Mailhog | `email`/WRITE (`:42`) |
| `GET /v1/email/parse-failures` | `:56-65` | List, optional `?resolved=` | `email`/READ (`:59`) |
| `POST /v1/email/parse-failures/{id}/resolve` | `:68-80` | Mark resolved | `email`/WRITE (`:72`) |

## 7. What it would take to connect a real mailbox

**Nothing generic exists today for real IMAP/Graph — only Mailhog HTTP works.**

- `MailboxProvider.IMAP`/`GRAPH` enum values can be selected on a `Mailbox` row, but
  `sync_mailbox` immediately raises `NotImplementedError` for anything but `MAILHOG`
  (`sync.py:22-23`, enforced by test).
- **No IMAP client code anywhere** (no `imaplib`/`imapclient` usage in `app/`).
- **No OAuth/Graph API code anywhere** (no MSAL, no token refresh logic).
- `MAILHOG_API_BASE` is a hardcoded literal, not derived from `settings.smtp_host`/
  `smtp_port` — **those settings are effectively dead config today**; nothing in `app/`
  reads them (only `backend/tests/test_email.py` hardcodes host/port directly, for its own
  test-simulation purposes).
- **Bottom line**: connecting a real mailbox requires writing a new connector module
  (real MIME parsing, since Mailhog pre-parses that for you), extending `sync_mailbox` to
  dispatch on `mailbox.provider` instead of hard-rejecting, and adding real credential/
  OAuth handling. Swapping `SMTP_HOST`/`SMTP_PORT` env vars alone changes nothing about
  inbound sync.

## 8. Outbound sending — there is none in application code

**No `smtplib`/SMTP-send code exists in `app/`.** The only `smtplib` usage in the entire
backend is `backend/tests/test_email.py:1,30-36` — and that's test scaffolding that
*simulates a customer sending an inbound email into Mailhog* for the integration tests,
not an outbound-reply feature:
```python
with smtplib.SMTP("127.0.0.1", 1026, timeout=5) as smtp:
    smtp.sendmail("customer@example.com", [to_addr], msg.as_string())
```
Whatever `auto_reply`/`draft_reply` decisions the AI pipeline produces are stored as data
(a `Message`/`Decision` row) — they are never actually emailed to the customer. If a
request arrived via the web portal, the reply is shown to the customer in-browser at
submit time; if it arrived via email, there is no code path that sends anything back.

## 9. Known limitations (explicit, from code comments)

- Mailhog is explicitly a "local dev/test stand-in for real IMAP/Graph"
  (`mailhog_client.py:1-4`) — Mailhog pre-parses MIME, a real connector would need to do
  that itself.
- Mailhog is a single shared catch-all inbox, unlike real per-mailbox IMAP/Graph accounts
  — `sync_mailbox` filters by recipient as a workaround (`mailhog_client.py:24-27`).
- Mailhog has no read/unread concept, so processed messages are deleted rather than
  marked seen (`mailhog_client.py:49-50`).
- Only the `mailhog` provider is wired up "in this build" (`sync.py:22-23`) — the
  `IMAP`/`GRAPH` enum values are placeholders for future work.
- **Not code-commented, but worth flagging directly**: email is disconnected from
  classification (§5) and from any real transport in both directions (§7, §8) — treat
  the email module as a working intake/triage tool for a local dev inbox, not a
  production-ready email channel.
