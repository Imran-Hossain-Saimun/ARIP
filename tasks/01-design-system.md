# Increment 1 — Design-system package + repo scaffold

**Status:** done

## Scope
Ship §04 as code first: tokens, primitives, project scaffold. Nothing downstream invents
its own styling.

## Deliverables
- `backend/` FastAPI skeleton, `frontend/` Vite + React + TS + Tailwind v4 scaffold
- `docker-compose.yml`: postgres(pgvector) on 5434, redis on 6380, minio, mailhog
- Design tokens (`frontend/src/design-system/tokens.css`) as Tailwind v4 `@theme`,
  matching §04 colors/type/spacing/radius/elevation exactly
- Primitives (`frontend/src/design-system/primitives/`): StatusBadge, ConfidenceMeter,
  CitationChip, DataTable (virtualized via TanStack Table + Virtual), Drawer, EmptyState,
  ErrorState, SkeletonRow — each with the states/props called out in §04
- `frontend/src/App.tsx` → later moved to `src/app/DesignSystemGallery.tsx` (route
  `/design-system`) as a living reference for the primitives

## Verification
- `npm run build` — 92KB gzip JS (budget: 250KB)
- `npm run test` (vitest) — all primitive tests passing
- `tsc -b` clean

## Notes
- Storybook (mentioned in spec's per-screen DoD) intentionally NOT set up — flagged as a
  gap, not silently dropped. Revisit if per-component visual QA becomes a bottleneck.
