# Increment 10 — OpenRouter chat provider (post-build addition)

**Status:** delivered

## Context
Not part of the original 9-increment plan — added after the full build was done, because
the user has an OpenRouter API key but no direct Anthropic/OpenAI key.

## Scope
Make the AI decision pipeline's chat/classification step work with an OpenRouter key,
with no other behavior change when Anthropic/OpenAI keys are used instead.

## Delivered
- `backend/app/ai/providers/chat.py`: `OpenRouterChatProvider` — OpenAI SDK pointed at
  `https://openrouter.ai/api/v1`, optional `HTTP-Referer`/`X-Title` attribution headers.
- `backend/app/core/config.py`: `openrouter_api_key`, `openrouter_model` (default
  `openai/gpt-4o-mini`), `openrouter_site_url`, `openrouter_site_name`.
- `get_chat_provider()` priority: Anthropic → OpenRouter → heuristic keyword fallback.
- `backend/.env.example` documents the new vars and the embeddings limitation.
- No new dependency — reuses the `openai` package already installed for
  `OpenAIEmbeddingProvider`.

## Verification
- 89 backend pytest still pass (no keys set in test env → heuristic fallback, unchanged).
- Provider-selection sanity check: `OPENROUTER_API_KEY` set, `ANTHROPIC_API_KEY` unset →
  `get_chat_provider()` returns `OpenRouterChatProvider` with the configured model.
- Live test with the user's real OpenRouter key: classified a sample dispute message
  correctly (`category: Billing`, `intent: dispute_charge`, `intent_certainty: 0.9`) via
  `openai/gpt-4o-mini`.

## Known limitation (not a bug)
OpenRouter has no embeddings endpoint (confirmed against their API reference — only
`/chat/completions` and `/generation`). So `OPENROUTER_API_KEY` alone does not upgrade
`providers/embeddings.py` off the deterministic-hash fallback; real semantic vector search
still needs `OPENAI_API_KEY`.
