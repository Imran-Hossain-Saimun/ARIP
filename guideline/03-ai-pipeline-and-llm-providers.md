# AI Decision Pipeline & LLM Providers

Covers: `backend/app/ai/pipeline.py`, `backend/app/ai/providers/{chat,embeddings}.py`,
`backend/app/ai/router.py`, `backend/app/core/config.py`.

This is the single most important file in the codebase to understand: `run_pipeline()`
is the one function that turns a raw customer message into a classified, scored,
rule-checked decision. Both the customer portal and the staff sandbox call it directly —
there is no separate/simplified simulation path.

## 1. `run_pipeline()` stage by stage

`backend/app/ai/pipeline.py:53-146`. Signature:
```python
run_pipeline(db, *, customer_email, customer_name, channel, subject, body) -> PipelineResult
```

Timing: a `stages: list[PipelineStage]` accumulator and a `perf_counter()` cursor (`:54-55`).
`_timed(stages, key, start, meta)` (`:40-42`) appends one `PipelineStage(key, ms, meta)`
per stage and resets the cursor — so each stage's `ms` is wall-clock time *since the
previous stage boundary*, not cumulative from pipeline start.

| Stage | Lines | What it does |
|---|---|---|
| 1. Intake | `:57-68` | Find-or-create `Customer` by email; create `Request` (`reference=f"REQ-{uuid4().hex[:8].upper()}"`, `status=PROCESSING`); add the initial customer `Message` |
| 2. Classify | `:70-75` | **LLM call #1**: `get_chat_provider().classify(f"{subject}\n{body}")` (`:71`) → sets `request.language`/`intent`/`category` |
| 3. Retrieval | `:77-79` | **LLM call #2** (embedding, inside `hybrid_search`): `hybrid_search(db, body, get_embedding_provider(), top_k=8, min_score=0.0)` (`:78`) |
| 4. Confidence | `:81-85` | See formula below |
| 5. Business rules | `:87-97` | Queries active `business_rule` `ConfigResource` rows, first match wins (see §3) |
| 6. Decision | `:99-115` | Branches on rule override then confidence thresholds (see §4) |

**Persistence** (`:117-144`, all in one transaction, committed at `:142`):
- One `Decision` row (`:117-129`). Notable hardcoded fields: `threshold` is *always*
  `CONFIDENCE_THRESHOLDS["auto_reply"]` (0.95) regardless of which band actually applied
  (`:121`); `model` is *always* the literal string `"claude-sonnet-4.6"` regardless of
  which chat provider actually ran (`:124`); `signals.source_recency` is a hardcoded `0.9`
  constant (`:122`); `signals.question_coverage` just duplicates `intent_certainty`.
- Up to 5 `Evidence` rows, one per `results[:5]` (`:131-132`).
- One `RuleEvaluation` row if a rule matched (`:134-135`).
- If decision is `AUTO_REPLY`/`DRAFT_REPLY`, an AI `Message` is added — **a hardcoded
  template string**, not LLM-generated reply text: `f"Thanks for reaching out — here's
  what I found regarding your {category}."` (`:137-138`).
- Two audit events: `decision.recorded` and `request.created` (`:140-141`).

## 2. Confidence formula (`:81-85`)

```python
retrieval_signal = max((r.score for r in results), default=0.0)
intent_certainty = float(classification.get("intent_certainty", 0.5))
confidence = round(min(0.99, 0.5 * retrieval_signal + 0.5 * intent_certainty), 4)
```
Equal-weighted average of the strongest retrieval hit and the classifier's stated
certainty, capped at 0.99.

## 3. Business-rule matching (`:87-97`)

```python
active_rules = db.execute(select(ConfigResource).where(
    ConfigResource.kind == ConfigResourceKind.BUSINESS_RULE,
    ConfigResource.status == ConfigResourceStatus.ACTIVE,
)).scalars()
matched_rule = None
for rule in active_rules:
    if _match_rule(rule.config.get("when", {}), request.category or "", request.intent or ""):
        matched_rule = rule
        break
```
No ordering, no priority sort — **first match in whatever order the query returns wins**,
iteration stops immediately (`break`). See
[05-automation-versioned-config.md](05-automation-versioned-config.md) for how these
`ConfigResource` rows are authored/published — same table, same `kind`, same `ACTIVE`
filter as the automation subsystem's lifecycle.

`_match_rule(when, category, intent)` (`:45-50`):
```python
if "category" in when and when["category"] != category: return False
if "intent" in when and when["intent"] != intent: return False
return bool(when)   # an empty WHEN clause never matches — it would fire on everything
```
Exact-string equality only; any other keys in `when` are ignored.

## 4. Decision branching (`:99-115`)

```python
CONFIDENCE_THRESHOLDS = {"auto_reply": 0.95, "draft_reply": 0.80, "ask_clarification": 0.60}   # :23
```

```
matched_rule?                       → HOLD              (request → HELD)
else confidence >= 0.95             → AUTO_REPLY         (request → ANSWERED)
else confidence >= 0.80             → DRAFT_REPLY        (request → AWAITING_APPROVAL)
else confidence >= 0.60             → ASK_CLARIFICATION  (request → AWAITING_CUSTOMER)
else                                 → ROUTE              (request → ROUTED)
```
**A matched rule is a full, unconditional short-circuit** — confidence is still computed
and stored, but plays no role in the outcome once a rule matches; the rule check runs
first (`:100`).

## 5. Chat providers (`backend/app/ai/providers/chat.py`)

Module docstring (`:1-10`): a real Anthropic- or OpenRouter-backed provider when a key is
configured, else a deterministic keyword fallback — "OpenRouter... does NOT expose an
embeddings endpoint, so `OPENROUTER_API_KEY` alone doesn't upgrade
`providers/embeddings.py` off its deterministic fallback."

**`HeuristicChatProvider`** (`:54-62`) — zero external calls, pure keyword matching via
`_keyword_classify()` (`:40-57`):
- `_CATEGORY_KEYWORDS` (`:10-17`): `Legal`, `Compliance`, `Billing`, `Technical Support`,
  `Complaint`, `General Inquiry` (default, empty keyword list).
- `_INTENT_KEYWORDS` (`:19-26`): `dispute_charge`, `login_issue`, `address_change`,
  `rate_question`, `kyc_update`, `general_question` (default).
- First keyword match in each map scores `0.9`; no match falls to the default at `0.55`.
- `language` is always hardcoded `"en"`.

**`AnthropicChatProvider`** (`:59-78`) — lazily imports `anthropic.Anthropic`, calls
`messages.create(model="claude-sonnet-4.6", max_tokens=200, ...)` (`:74`) with a prompt
asking for a strict JSON object (`language`/`category`/`intent`/`intent_certainty`). On
malformed JSON output, falls back to `_keyword_classify` rather than crashing the
pipeline (`:77-78`).

**`OpenRouterChatProvider`** (added post-build; see
`tasks/10-openrouter-provider.md`) — OpenAI SDK pointed at
`https://openrouter.ai/api/v1`, `chat.completions.create(model=self._model, ...)` with
the identical classification prompt, same malformed-JSON fallback behavior. Optional
`HTTP-Referer`/`X-Title` attribution headers from `settings.openrouter_site_url`/
`openrouter_site_name`.

**Provider selection priority** — `get_chat_provider()`:
```python
if settings.anthropic_api_key:  return AnthropicChatProvider(...)
if settings.openrouter_api_key: return OpenRouterChatProvider(...)
return HeuristicChatProvider()
```
`Anthropic → OpenRouter → heuristic`. Config fields (`backend/app/core/config.py`):
`anthropic_api_key`, `openai_api_key`, `openrouter_api_key`, `openrouter_model` (default
`"openai/gpt-4o-mini"`), `openrouter_site_url`, `openrouter_site_name`.

## 6. Embedding providers — pipeline-facing view

`get_embedding_provider()` is called fresh on every pipeline run (no caching) at
`pipeline.py:78`, inside `hybrid_search`. Full detail in
[02-knowledge-and-retrieval.md](02-knowledge-and-retrieval.md) §3. Key point for this doc:
**only `OPENAI_API_KEY` affects embedding quality** — Anthropic/OpenRouter keys have zero
effect here.

## 7. Every LLM invocation call site — the complete list

1. **Classification** — `pipeline.py:71` → `get_chat_provider().classify(...)` →
   dispatches to `chat.py:74` (Anthropic), `chat.py:108`-equivalent (OpenRouter), or pure
   keyword matching (heuristic, no external call).
2. **Embedding** — `pipeline.py:78` (via `hybrid_search`) →
   `knowledge/retrieval.py:72` → `embedding_provider.embed([query_text])` → dispatches to
   `embeddings.py:38` (OpenAI `text-embedding-3-small`) or a deterministic hash (no
   external call).

No other `.classify()` or `.embed()` call sites exist anywhere in `app/`. Both the staff
sandbox and the customer portal hit exactly these same two call sites indirectly through
`run_pipeline` — there is no duplicate/parallel LLM invocation path.

## 8. Staff sandbox vs. customer portal

**`POST /v1/ai/run`** (`backend/app/ai/router.py:14-31`) — permission
`decision_trace`/WRITE (`:18`). Docstring: "runs the exact same pipeline the public
portal endpoint uses, so what you see here is what customers get" (`:20-21`). Returns the
full `RunPipelineResponse`: request id/reference, decision id/type/confidence,
`rule_overridden`, and the complete per-stage timing/meta breakdown — intended for the
`AiPipelineMonitor` frontend screen.

**`POST /v1/portal/requests`** (`backend/app/portal/router.py:54-71`) — no auth at all.
Hardcodes `channel=Channel.WEB` (vs. the sandbox accepting any channel in the request
body). Response is customer-facing and much narrower: reference, status, `progress_stage`,
`ai_message`, and `citations` (only for `auto_reply`/`draft_reply`) — no stage timings, no
confidence score, no rule-override flag exposed to the customer.

## 9. Known limitations (from code comments)

- `Decision.threshold`/`Decision.model`/`signals.source_recency` are hardcoded, not
  computed from what actually ran (`pipeline.py:121,122,124`).
- The AI-authored reply is a fixed template string, not real generated text
  (`pipeline.py:138`).
- Business-rule matching has no priority ordering — first match wins, whatever order the
  query happens to return (`pipeline.py:88-96`).
- An empty `when` clause deliberately never matches, to avoid a rule firing on everything
  (`pipeline.py:50`).
- Malformed LLM JSON output silently degrades to heuristic classification rather than
  surfacing an error (`chat.py:77-78` and OpenRouter equivalent).
- OpenRouter has no embeddings endpoint — `OPENROUTER_API_KEY` alone does not improve
  retrieval quality (`chat.py:1-10`).
