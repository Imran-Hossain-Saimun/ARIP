"""Pluggable classification/generation provider (FR-088), mirroring
`providers/embeddings.py`'s pattern: a real Anthropic- or OpenRouter-backed provider when
an API key is configured, else a deterministic keyword-based fallback so the full
intake→decision pipeline runs end-to-end with zero external config.

OpenRouter (https://openrouter.ai) proxies chat completions for many model providers
behind a single OpenAI-compatible API — useful when you have an OpenRouter key but not a
direct Anthropic/OpenAI one. It does NOT expose an embeddings endpoint, so
`OPENROUTER_API_KEY` alone doesn't upgrade `providers/embeddings.py` off its deterministic
fallback — set `OPENAI_API_KEY` for real embeddings, or accept non-semantic retrieval."""

from typing import Protocol

from app.core.config import get_settings

_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "Legal": ["legal", "lawsuit", "court", "subpoena"],
    "Compliance": ["kyc", "compliance", "regulatory", "sanction"],
    "Billing": ["fee", "charge", "refund", "statement", "invoice"],
    "Technical Support": ["login", "app", "error", "outage", "password", "otp"],
    "Complaint": ["complaint", "unhappy", "disappointed", "escalate"],
    "General Inquiry": [],
}

_INTENT_KEYWORDS: dict[str, list[str]] = {
    "dispute_charge": ["dispute", "unauthorized", "refund"],
    "login_issue": ["login", "password", "otp", "sign in"],
    "address_change": ["address", "move", "relocat"],
    "rate_question": ["rate", "interest", "pricing"],
    "kyc_update": ["kyc", "document", "verify"],
    "general_question": [],
}


class ClassifyResult(dict):
    language: str
    intent: str
    category: str
    intent_certainty: float


class ChatProvider(Protocol):
    def classify(self, text: str) -> dict: ...


def _keyword_classify(text: str) -> dict:
    lower = text.lower()

    def best_match(keyword_map: dict[str, list[str]], default: str) -> tuple[str, float]:
        for label, keywords in keyword_map.items():
            if any(kw in lower for kw in keywords):
                return label, 0.9
        return default, 0.55

    category, cat_certainty = best_match(_CATEGORY_KEYWORDS, "General Inquiry")
    intent, intent_certainty = best_match(_INTENT_KEYWORDS, "general_question")
    return {"language": "en", "category": category, "intent": intent, "intent_certainty": min(cat_certainty, intent_certainty) if intent != "general_question" else intent_certainty}


class HeuristicChatProvider:
    def classify(self, text: str) -> dict:
        return _keyword_classify(text)


class AnthropicChatProvider:
    def __init__(self, api_key: str):
        from anthropic import Anthropic

        self._client = Anthropic(api_key=api_key)

    def classify(self, text: str) -> dict:
        import json

        prompt = (
            "Classify this customer request. Respond with ONLY a JSON object with keys "
            '"language" (ISO 639-1), "category" (one of: Legal, Compliance, Billing, '
            'Technical Support, Complaint, General Inquiry), "intent" (a short snake_case '
            'label), "intent_certainty" (0-1 float).\n\nRequest: ' + text
        )
        response = self._client.messages.create(model="claude-sonnet-4.6", max_tokens=200, messages=[{"role": "user", "content": prompt}])
        try:
            return json.loads(response.content[0].text)
        except (ValueError, IndexError, AttributeError):
            return _keyword_classify(text)  # malformed model output — fall back rather than crash the pipeline


class OpenRouterChatProvider:
    def __init__(self, api_key: str, model: str, site_url: str | None = None, site_name: str | None = None):
        from openai import OpenAI

        headers = {}
        if site_url:
            headers["HTTP-Referer"] = site_url
        if site_name:
            headers["X-Title"] = site_name
        self._client = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1", default_headers=headers or None)
        self._model = model

    def classify(self, text: str) -> dict:
        import json

        prompt = (
            "Classify this customer request. Respond with ONLY a JSON object with keys "
            '"language" (ISO 639-1), "category" (one of: Legal, Compliance, Billing, '
            'Technical Support, Complaint, General Inquiry), "intent" (a short snake_case '
            'label), "intent_certainty" (0-1 float).\n\nRequest: ' + text
        )
        response = self._client.chat.completions.create(model=self._model, max_tokens=200, messages=[{"role": "user", "content": prompt}])
        try:
            return json.loads(response.choices[0].message.content)
        except (ValueError, IndexError, AttributeError, TypeError):
            return _keyword_classify(text)  # malformed model output — fall back rather than crash the pipeline


def get_chat_provider() -> ChatProvider:
    settings = get_settings()
    if settings.anthropic_api_key:
        return AnthropicChatProvider(settings.anthropic_api_key)
    if settings.openrouter_api_key:
        return OpenRouterChatProvider(settings.openrouter_api_key, settings.openrouter_model, settings.openrouter_site_url, settings.openrouter_site_name)
    return HeuristicChatProvider()
