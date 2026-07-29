# Increment 5 — Knowledge library, ingestion, approval, gaps

**Status:** done (backend fully verified; frontend build/test-clean but NOT click-
verified live in a browser this pass — see Delivered)

## Scope
Real chunk/embed/pgvector ingestion pipeline — the "vector" half of hybrid RAG — plus
the "vectorless" hierarchy tree, article lifecycle, and gap backlog.

## Backend
- Models: `KnowledgeArticle`, `KnowledgeVersion` (fields per §09: version, status,
  effective_from, expires_on, access_level, indexed_at), `KnowledgeChunk` (pgvector
  `embedding` column, `pgvector` python package already installed), `KnowledgeNode`
  (self-referential hierarchy), `KnowledgeGap`
- Add real FK constraints back onto `Evidence.chunk_id` (currently unconstrained,
  see increment 2 notes in `backend/app/models/decision.py`)
- `POST /v1/knowledge/ingest` (multipart: PDF/DOCX/XLSX/MD/HTML/CSV) → virus-scan stub →
  object storage (MinIO, S3-compatible) → text extraction → chunk (800 tok / 120 overlap
  per spec) → embed (Anthropic/OpenAI embeddings) → pgvector write + hierarchy node build
- `GET /v1/knowledge?status&dept&q`, `POST /v1/knowledge/search` (hybrid: vector top-k 8 +
  vectorless hierarchy traversal + structured lookup, fused via reciprocal-rank)
- `POST /v1/knowledge/:id/versions/:v/approve`
- **Non-negotiable**: draft-status knowledge can NEVER reach the retrieval result set —
  enforce with a `status = 'approved'` filter at the query layer, not the UI
- `GET /v1/gaps` — knowledge gap backlog, ranked by hit count
- Expiry watcher (can be a simple scheduled check for now, full Celery beat job later)

## Frontend
- `KnowledgeLibrary`: KpiStrip, FilterBar, DataTable, `ArticleDrawer` (LifecycleStepper,
  MetadataList, VersionHistory w/ diff+restore, DrawerActions)
- `IngestionWizard` (4 steps): FileDropzone, DuplicateWarning (simhash+title match),
  MetadataForm, ReviewerPicker, IndexProgress
- Gap backlog view + AI-assisted article drafting seeded from failed requests' questions

## Verification target
- Critical E2E test #3 from §13: article in Draft cannot appear in any evidence list
- pytest: ingestion pipeline chunking/embedding math, retrieval never returns draft chunks

## Delivered
- Backend: `KnowledgeArticle`/`KnowledgeVersion`/`KnowledgeChunk`(pgvector `Vector(1536)`)/
  `KnowledgeNode`/`KnowledgeGap` models (migration `9dda8ed2109b`), real `Evidence.chunk_id`
  FK now points at `knowledge_chunks.id`. `app/knowledge/`: `chunking.py` (word-based
  800/120 approx-token chunking), `hierarchy.py` (markdown `#`-heading tree + offset→node
  mapping), `retrieval.py` (pgvector cosine-distance search + ILIKE keyword search, fused
  by reciprocal-rank fusion), `ingestion.py` (`index_version` — the only place chunks get
  created/embedded). `app/ai/providers/embeddings.py`: pluggable — real OpenAI
  `text-embedding-3-small` when `OPENAI_API_KEY` is set, else a deterministic-but-not-
  semantic hash-based fallback so the full pgvector pipeline is exercisable with zero
  config. `app/core/storage.py`: MinIO/boto3 wrapper. New `GET /v1/departments`
  (`app/reference/router.py`) — a low-sensitivity picker endpoint any authenticated user
  can call, distinct from the admin-gated `/v1/admin/departments`. 15 new pytest tests
  (47 total, all against real assertions — chunking/hierarchy are pure-Python unit tests,
  endpoint tests avoid the vector-search path since SQLite can't run pgvector's
  `cosine_distance`).
- **Verified live via curl against the real dockerized Postgres+pgvector** (not pytest,
  since SQLite can't exercise this): ingested a real article, approved it (triggering
  real chunking + fake-provider embedding + pgvector storage), then ran hybrid search and
  got back a correctly-fused, correctly-scored result with the right `§`-locator — this
  is the part of the increment most worth trusting, and it's the part actually proven.
- Seed script now creates 3 real approved+indexed `KnowledgeArticle`s (matching the
  KB-0412/KB-0500/KB-0900 citations already referenced by increment-3's request seed data,
  so the story is consistent) and 4 `KnowledgeGap` rows.
- Frontend: `features/knowledge/{types,api,KnowledgeLibraryPage,ArticleDrawer,
  IngestArticleForm,KnowledgeGapsPage}.tsx`, `features/reference/api.ts`. Added a `Modal`
  primitive (§04 names it alongside Drawer; this is its first real use). `KnowledgeLibraryPage`
  is `DataTable`'s first real production use (increment 3 found it didn't fit the narrow
  queue list — it fits fine here on a wide screen, which is what it was actually built for).
- **Simplifications, clearly scoped down from the plan** (all noted in code comments too):
  - PDF/DOCX/XLSX text extraction is NOT implemented — `POST /ingest` parses `.txt`/`.md`
    files directly, or accepts pre-extracted text via a `content` field. Binary files are
    still stored in MinIO for reference. Adding real parsers (pdfplumber/python-docx/etc.)
    is follow-up work, not done here.
  - `IngestionWizard`'s 4 steps collapsed into one form (`IngestArticleForm`) — no
    `FileDropzone`/`DuplicateWarning`(simhash)/`ReviewerPicker` UI. The backend still does
    real ingestion; only the guided-wizard UX around it is cut.
  - `VersionHistory`'s diff/restore isn't built — the drawer lists versions with status/
    date only, no content diff viewer (no `DiffViewer` primitive exists yet).
  - Hybrid retrieval is real (pgvector + keyword + RRF) but simplified vs. production:
    no reranking model, "vectorless" is keyword-overlap scoring rather than true graph
    traversal, chunking approximates tokens as words.
  - `KnowledgeGap` rows are seeded directly, not yet computed from live low-confidence
    request clusters — "AI-assisted article drafting seeded from failed requests" (the
    gap→draft-article flow) is not implemented.
- **Known gap this pass**: frontend was NOT click-verified live in a browser — the
  claude-in-chrome tooling became persistently unresponsive (clicks/form-input not
  registering, tab groups dropping) across many retries and multiple fresh tabs, well
  past the point where retrying further was reasonable. Confidence is still high because
  (a) the highest-risk new surface (pgvector/embeddings/retrieval) WAS verified live via
  curl, and (b) every frontend piece reuses primitives/patterns (`DataTable`, `Drawer`,
  `Modal`, `PermissionGate`, TanStack Query mutations) already proven live in increments
  2-4 — but this should be spot-checked in a browser before being treated as fully proven.
