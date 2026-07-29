"""Thin client for Mailhog's HTTP API (local dev/test stand-in for real IMAP/Graph —
see MailboxProvider.MAILHOG). Mailhog already parses MIME for us, so there's no raw
message parsing to do here — a real IMAP/Graph connector (increment-6-and-beyond, when a
real mailbox is wired in) would need actual MIME parsing where this client doesn't."""

from dataclasses import dataclass

import httpx

MAILHOG_API_BASE = "http://127.0.0.1:8025/api/v2"


@dataclass
class InboundMessage:
    external_id: str
    from_email: str
    to_addresses: list[str]
    subject: str
    body: str
    raw: dict


def fetch_messages(limit: int = 50) -> list[InboundMessage]:
    """Mailhog is a single shared catch-all SMTP sink — it doesn't route by recipient the
    way real per-mailbox IMAP/Graph accounts would, so every configured Mailbox pulls from
    the same message pool. `sync_mailbox` filters by `to_addresses` to keep mailboxes
    logically separate; this is still a simplification worth knowing about."""
    response = httpx.get(f"{MAILHOG_API_BASE}/messages", params={"limit": limit})
    response.raise_for_status()
    payload = response.json()

    messages = []
    for item in payload.get("items", []):
        to_addresses = [f"{to['Mailbox']}@{to['Domain']}" for to in item.get("To") or []]
        messages.append(
            InboundMessage(
                external_id=item["ID"],
                from_email=f"{item['From']['Mailbox']}@{item['From']['Domain']}" if item.get("From") else "",
                to_addresses=to_addresses,
                subject=(item.get("Content", {}).get("Headers", {}).get("Subject") or [""])[0],
                body=item.get("Content", {}).get("Body", ""),
                raw=item,
            )
        )
    return messages


def delete_message(message_id: str) -> None:
    """Mailhog has no read/unread concept — delete processed messages so re-sync doesn't
    reprocess them. A real IMAP connector would mark \\Seen or move to a processed folder."""
    httpx.delete(f"{MAILHOG_API_BASE}/messages/{message_id}")
