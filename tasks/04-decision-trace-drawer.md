# Increment 4 — Decision trace drawer + evidence tab

**Status:** done

## Scope
Consumes `GET /v1/decisions/:id/trace` exactly as shaped in §09.

## Backend
- `GET /v1/decisions/:id/trace` — assembles the exact JSON shape from §09: decision_id,
  request_id, type, confidence, threshold, signals (intent_certainty, retrieval_agreement,
  question_coverage, source_recency), stages[] (key/ms/meta), evidence[] (chunk_id,
  article, version, locator, mode, score), rules[] (id/outcome/priority), model,
  prompt_version, audit_hash
- `POST /v1/decisions/:id/replay` — re-run the decision pipeline against the same input
  (stub the AI call for now if increment 9's real pipeline isn't ready; real replay lands
  properly once increment 9's AI service exists — note the simplification if taken)
- `GET /v1/requests/:id/decisions` — list decisions for a request (a request may have
  several over its life)

## Frontend
- `Drawer` (already built) hosting: `PipelineStepper` (stages), `ExplanationCard` ("why
  this decision" — confidence vs threshold, signals breakdown), `EvidenceCard[]` w/
  `CitationChip`, `RuleEvaluationTable`, `TraceActions` (Replay/Export)
- Wire into `RequestRecord`'s AI Decision + Evidence tabs from increment 3
- `ConfidenceMeter` (already built) showing value vs threshold marker

## Verification target
- Critical E2E test #2 from §13: rule override — high-confidence Legal request never
  auto-sends, shows the hold banner (BR-022 style)
- Critical E2E test #3: draft knowledge is never cited — enforce at the query level in
  increment 5's retrieval, but the trace UI here must never render a Draft-status article
  even if the API were to return one (defense in depth)

## Delivered
- Backend: `Decision` model gained `threshold` (Numeric, default 0.95) and `stages` (JSON
  list) columns (migration `ff9678fcb995`, with `server_default` so it applies cleanly to
  existing rows). `app/decisions/router.py`: `GET /v1/decisions/:id/trace` (exact §09
  shape — decision_id, request_id as the human reference, type, confidence, threshold,
  signals, stages, evidence, rules, model, prompt_version, audit_hash pulled from the
  matching `AuditEvent.hash`), `POST /v1/decisions/:id/replay` (stub — see simplification
  below), `GET /v1/requests/:id/decisions`. Department-scoped like increment 3's requests.
  Seed script now writes a `decision.recorded` audit event per decision (the only way a
  trace gets an `audit_hash`) and populates 3-stage pipeline timings. 7 new pytest tests
  (32 total).
- Frontend: `features/decisions/{types,api,DecisionTraceDrawer}.tsx` — pipeline stepper
  (proportional bars), signals grid, evidence chips, rule table, Replay + Export (client-
  side JSON download, no backend round-trip needed). `RequestRecord`'s AI Decision and
  Evidence tabs now render real content (confidence+signals+rules inline, full evidence
  list) instead of the increment-3 disabled placeholders; a "View full pipeline trace"
  link opens the drawer.
- **Bug found and fixed during verification**: the queue's global `Escape` handler
  (deselect the row) and the `Drawer` primitive's own `Escape` handler (close the drawer)
  both fired on the same keypress — closing the trace drawer also silently reset the
  selected row back to the top of the list. Removed the queue-level Escape-to-deselect
  behavior entirely (§04 only specifies Escape for closing an open panel, not deselecting).
- **Simplification not in the original plan**: `POST /replay` doesn't re-run anything yet
  — the real AI pipeline is increment 9's deliverable. Today it validates the decision
  exists/is accessible and returns a message explaining that. `prompt_version` in the
  trace response is always `null` until `PromptVersion` lands in increment 7.
- **Verified live in Chrome**: AI Decision tab renders signals/rule table for a rule-held
  decision, "View full pipeline trace" opens the drawer with correct pipeline timings/
  evidence/audit hash, Replay returns its stub message, Export downloads, and Escape
  closes only the drawer (selection preserved) after the fix above.
