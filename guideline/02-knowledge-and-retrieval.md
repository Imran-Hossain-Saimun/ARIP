# Document Processing & Retrieval

Covers: `backend/app/knowledge/{chunking,hierarchy,ingestion,retrieval,router}.py`,
`backend/app/models/knowledge.py`, `backend/app/ai/providers/embeddings.py`.

## 1. Data model

`EMBEDDING_DIM = 1536` (`backend/app/models/knowledge.py:12`) — fixed to match OpenAI's
`text-embedding-3-small` output size, so the pgvector column never needs to change width
when swapping embedding providers.

**`KnowledgeVersionStatus`** (`:15-25`): `DRAFT`, `REVIEW`, `APPROVED`, `INDEXED`,
`ARCHIVED`. Important nuance (`:16-19`): the conceptual "Approved" and "available to AI"
stages are collapsed — a version becomes queryable by retrieval the instant it hits
`APPROVED`; `INDEXED` only signals the chunk/embed step finished, it's not a separate
access gate.

**`AccessLevel`** (`:28-31`): `PUBLIC`, `INTERNAL`, `RESTRICTED`.

**`KnowledgeArticle`** (`:34-43`): `title`, `department_id` FK (SET NULL), `category`,
`tags` (JSON list). Has many `versions` (newest first).

**`KnowledgeVersion`** (`:46-65`): `article_id` FK CASCADE, `version` string, `status`
(default `DRAFT`), `effective_from`/`expires_on`, `access_level` (default `INTERNAL`),
`indexed_at`, `content` (the extracted plain text this version was chunked from),
`storage_key` (object-storage key for the originally uploaded file, if any),
`reviewer_id` FK (SET NULL). `nodes`/`chunks` relationships both cascade
`all, delete-orphan` (`:64-65`) — this is what lets re-indexing simply clear and rebuild.

**`KnowledgeNode`** (`:68-79`) — self-referential hierarchy tree, one per version:
`parent_id` FK to `knowledge_nodes.id`, `title`, `locator` (e.g. `"§3.1"`), `order_index`.

**`KnowledgeChunk`** (`:82-95`): `version_id` FK CASCADE, `node_id` FK SET NULL (nullable
— e.g. preamble text before any heading), `chunk_index`, `content`, `embedding`
(`Vector(1536)`, pgvector column).

**`KnowledgeGapStatus`** (`:98-101`): `OPEN`, `DRAFTING`, `CLOSED`.
**`KnowledgeGap`** (`:104-111`) — standalone table, not linked to any article/version:
`cluster_key`, `occurrence_count`, `avg_confidence`, `status` (default `OPEN`),
`sample_request_refs` (JSON list).

## 2. Ingestion flow — exactly what's accepted

**Only three ways to get text indexed** (`backend/app/knowledge/router.py:86-137`,
docstring `:99-102`):
1. Pasted text via the `content` form field.
2. Uploading a `.txt` file (decoded UTF-8, `errors="replace"`).
3. Uploading a `.md` file (same decoding).

**No PDF/DOCX/XLSX text extraction exists.** Other file types are still uploaded to
object storage via `upload_document(...)` (`:106-108`) for reference, but the text has to
be supplied separately via `content` for indexing to happen at all. If, after all this,
the extracted text is empty, the endpoint 400s (`:112-116`).

### Call chain: submit → chunks + embeddings stored

1. **`POST /v1/knowledge/ingest`** (`:86-137`, permission `knowledge_authoring`/WRITE)
   creates the `KnowledgeArticle` and a `DRAFT` `KnowledgeVersion` — **not yet chunked or
   embedded**. `chunk_count`/`node_count` in the response are hardcoded `0` (`:137`)
   because indexing hasn't happened yet. Records `knowledge.ingested` audit event.
2. **`POST /v1/knowledge/{article_id}/versions/{version}/approve`** (`:140-168`,
   permission `knowledge_approval`/APPROVE) — docstring: "this is the ONLY place a
   version's chunks get embedded/indexed" (`:148-150`), enforcing the non-negotiable that
   draft knowledge can never reach retrieval. Sets `status=APPROVED`, `reviewer_id`, calls
   **`index_version(db, kv, get_embedding_provider())`** (`:162`), then sets
   `status=INDEXED` (`:163`). Records `knowledge.approved` audit event.
3. **`index_version()`** (`backend/app/knowledge/ingestion.py:10-53`) — safe to call
   again (re-approval rebuilds cleanly since nodes/chunks cascade-delete first, `:14-16`):
   - `parse_hierarchy(text)` (`:19`) builds the heading tree (see §5).
   - Creates a `KnowledgeNode` row per hierarchy node, then wires up `parent_id` in a
     second pass once IDs are flushed (`:20-29`).
   - `chunk_text(text)` (`:31`) splits into pieces (constants below).
   - `embedding_provider.embed(pieces)` (`:33`) — **one batch call** for the whole
     version.
   - For each `(piece, embedding)`: finds the character offset via a fuzzy
     `text.find(piece[:30], search_cursor)` lookup, then `find_node_for_offset()` to
     attach it to the right hierarchy node (`:34-41`); creates the `KnowledgeChunk` row.
   - Stamps `version.indexed_at = utcnow()` (`:52-53`).

### Chunking constants

`backend/app/knowledge/chunking.py:5-6`:
```python
CHUNK_SIZE_WORDS = 800
CHUNK_OVERLAP_WORDS = 120
```
Whitespace-word split, not a real tokenizer (`:1-3`) — "close enough for chunk
boundaries in this build, not byte-for-byte what a production tokenizer would produce."
`chunk_text()` (`:9-23`) walks the word list with `step = chunk_size - overlap = 680`
words per stride.

## 3. Embedding provider selection

`backend/app/ai/providers/embeddings.py`:
```python
def get_embedding_provider() -> EmbeddingProvider:      # :42-46
    settings = get_settings()
    if settings.openai_api_key:
        return OpenAIEmbeddingProvider(settings.openai_api_key)
    return DeterministicHashEmbeddingProvider()
```
- **`OpenAIEmbeddingProvider`** (`:31-39`) calls `embeddings.create(model=
  "text-embedding-3-small", input=texts)` (`:38`).
- **`DeterministicHashEmbeddingProvider`** (`:17-28`) seeds `random.Random` from
  `sha256(text)` and draws 1536 uniform floats — deterministic (same text → same vector)
  but **not semantically meaningful** (`:18-20`). Silent fallback: no warning is raised
  anywhere when this is what's actually running.
- **Only `OPENAI_API_KEY` affects this.** `ANTHROPIC_API_KEY`/`OPENROUTER_API_KEY` have no
  effect on embedding provider selection — OpenRouter has no embeddings endpoint at all
  (see [03-ai-pipeline-and-llm-providers.md](03-ai-pipeline-and-llm-providers.md)).

## 4. Hybrid retrieval (`backend/app/knowledge/retrieval.py`)

Module docstring (`:1-6`): pgvector similarity ("vector" mode) + ILIKE keyword overlap
("vectorless" mode), fused by reciprocal-rank fusion. "No cross-encoder reranking, no
real vectorless 'graph traversal' beyond keyword scoring" — but the one hard guarantee
holds exactly: only `APPROVED`/`INDEXED` versions are ever queried.

```python
RETRIEVABLE_STATUSES = (KnowledgeVersionStatus.APPROVED, KnowledgeVersionStatus.INDEXED)  # :16
RRF_K = 60   # :17
```

**`vector_search(db, query_embedding, top_k)`** (`:27-44`):
- **Dialect guard** (`:33-34`): `if db.bind.dialect.name != "postgresql": return []` —
  pgvector's `<=>` cosine-distance operator is Postgres-only, and the pytest SQLite
  fixture can't run it, so this guard skips cleanly in tests rather than erroring. The
  vector half is instead verified separately against a real Postgres+pgvector container.
- Score = `1.0 - cosine_distance` (higher = more similar), ordered ascending by distance,
  limited to `top_k`.

**`keyword_search(db, query_text, top_k)`** (`:47-62`):
- Tokenizes the query (lowercase, whitespace split, terms with `len > 2` only).
- ILIKE-OR across all terms against `KnowledgeChunk.content`.
- Score = `(matching term count) / (total term count)`.

**`hybrid_search(db, query_text, embedding_provider, top_k=8, min_score=0.62)`**
(`:65-87`):
1. `embedding_provider.embed([query_text])[0]` (`:72`) — the actual embedding LLM call.
2. Runs both searches with the same `top_k`.
3. **Reciprocal Rank Fusion**: for each list, 1-based rank, accumulate
   `rrf_scores[chunk_id] += 1.0 / (RRF_K + rank)` (`:78-83`) — classic RRF with `k=60`.
   A chunk found by both methods keeps its **vector**-origin score/mode for display, even
   though its RRF ranking reflects both contributions (`:80,83`).
4. Ranks by RRF score, builds results in that order.
5. **Filters by `min_score` on the raw origin score** (cosine similarity or keyword-overlap
   ratio) — **not** the RRF fusion score, which is used only for ordering (`:87`).

Defaults: `top_k=8`, `min_score=0.62` on the function signature and the identical
defaults on `SearchRequest` (`backend/app/schemas/knowledge.py:48-51`), both overridable
per-request. Note the AI pipeline itself calls `hybrid_search` with `min_score=0.0`
(`backend/app/ai/pipeline.py:78`) — different threshold than the manual search endpoint.

## 5. Knowledge hierarchy (`backend/app/knowledge/hierarchy.py`)

Heuristic, not a real document AST (`:1-3`) — built from markdown `#`-style headings via
`_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)` (`:8`).

`parse_hierarchy(text)` (`:21-52`): if no headings at all, returns one synthetic root node
(`title="Document"`, `locator="§1"`). Otherwise walks matches with a level-stack to
determine nesting and per-level counters to build dotted locators (`§2.1` etc).

`find_node_for_offset(nodes, offset)` (`:55-63`) — linear scan for the *narrowest* span
containing the offset (not a true tree traversal).

**No dedicated hierarchy/tree endpoint exists.** The tree is only surfaced indirectly:
`SearchResultItem.locator` comes from `r.chunk.node.locator if r.chunk.node else "§1"`
(`backend/app/knowledge/router.py:187`).

## 6. Knowledge gaps

**No runtime code creates or updates a `KnowledgeGap` row.** The only inserts anywhere are
in the static demo seed script (`backend/seed/seed.py:313-314`). There is no automatic
"N low-confidence searches with the same cluster_key → gap" trigger, and no status-
transition endpoint beyond the read-only `GET /v1/gaps` list. The `DRAFTING`/`CLOSED`
statuses imply an intended workflow that isn't wired up.

## 7. Every endpoint (`backend/app/knowledge/router.py`)

Two routers: `router` (prefix `/v1/knowledge`) and `gaps_router` (prefix `/v1/gaps`).

| Method + path | Line | Purpose | Permission |
|---|---|---|---|
| `GET /v1/knowledge` | `:51-69` | List articles (with latest version), filter by status/dept/title | `knowledge_authoring`/READ (`:54`) |
| `GET /v1/knowledge/{id}` | `:72-83` | One article's full detail incl. all versions | `knowledge_authoring`/READ (`:76`) |
| `POST /v1/knowledge/ingest` | `:86-137` | Create article + draft version | `knowledge_authoring`/WRITE (`:89`) |
| `POST /v1/knowledge/{id}/versions/{version}/approve` | `:140-168` | Approve + index | `knowledge_approval`/APPROVE (`:146`) |
| `POST /v1/knowledge/search` | `:171-193` | Run `hybrid_search`, return ranked truncated (400-char) results | `knowledge_authoring`/READ (`:175`) |
| `GET /v1/gaps` | `:196-202` | List gaps, ordered by `occurrence_count desc` | `knowledge_authoring`/READ (`:199`) |

## 8. Known limitations (from code comments)

- No PDF/DOCX/XLSX text extraction — only `.txt`/`.md`/pasted `content`
  (`knowledge/router.py:99-102`).
- Chunking is word-split, not tokenizer-accurate (`knowledge/chunking.py:1-3`).
- Hierarchy parsing is regex-heuristic, chunk-to-node linking is fuzzy offset matching,
  not a real AST (`knowledge/hierarchy.py:1-3`, `ingestion.py:36-40`).
- No cross-encoder reranking; "vectorless" mode is keyword overlap only, not real graph
  traversal (`knowledge/retrieval.py:1-6`).
- Vector search silently returns `[]` on non-Postgres backends (`retrieval.py:28-34`) —
  intentional test-fixture accommodation, not a production concern.
- Deterministic hash embeddings are not semantically meaningful — silent fallback with no
  warning surfaced (`ai/providers/embeddings.py:18-20,42-46`).
- Ingest response's `chunk_count`/`node_count` are always `0` — real counts only exist
  after `approve` runs (`knowledge/router.py:137`).
- Knowledge gaps are never runtime-generated — seed data only (see §6).
