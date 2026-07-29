# ARIP build tasks

One file per increment from the build order in `project/ARIP Design.dc.html` §13. See
`C:\Users\saimun\.claude\plans\wise-hugging-scott.md` for the full architecture plan.

| # | File | Status |
|---|------|--------|
| 1 | [01-design-system.md](01-design-system.md) | done |
| 2 | [02-backend-skeleton-appshell.md](02-backend-skeleton-appshell.md) | done |
| 3 | [03-request-queue-core-loop.md](03-request-queue-core-loop.md) | done |
| 4 | [04-decision-trace-drawer.md](04-decision-trace-drawer.md) | done |
| 5 | [05-knowledge-module.md](05-knowledge-module.md) | done (frontend not browser-verified) |
| 6 | [06-email-processing.md](06-email-processing.md) | done (frontend not browser-verified) |
| 7 | [07-automation.md](07-automation.md) | done — verified live in Chrome |
| 8 | [08-analytics-audit-admin-settings.md](08-analytics-audit-admin-settings.md) | done — verified live in Chrome |
| 9 | [09-portal-pipeline-responsive.md](09-portal-pipeline-responsive.md) | done — verified live in Chrome |
| 10 | [10-openrouter-provider.md](10-openrouter-provider.md) | done — verified live with real key |

All 9 increments delivered. This closes the originally-scoped build. #10 is a post-build
addition (OpenRouter chat provider), not part of the original plan.

This directory is build history/changelog — what shipped, when, what was verified. For
how the app actually works today (data model, request lifecycle, AI pipeline, retrieval,
email, RBAC/audit, frontend↔backend map), see [`../guideline/`](../guideline/README.md).
