"""Stripe webhook handler with idempotency key enforcement.

After the refactor in this commit, idempotency keys are stored in a
module-level dict (simulating Postgres persistence) instead of being
scoped per request. This causes the integration test to fail because the
key from the first webhook call persists when the second call runs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

# Simulates Postgres idempotency_keys table — persists across requests
_idempotency_store: dict[str, datetime] = {}


def clear_idempotency_store() -> None:
    """Reset the store — must be called between test calls to avoid 409."""
    _idempotency_store.clear()


@dataclass
class WebhookResult:
    status_code: int
    body: dict


def handle_stripe_webhook(payload: dict) -> WebhookResult:
    """Process a Stripe webhook event with idempotency enforcement.

    Returns 200 on first delivery and on duplicate (idempotent behaviour).
    The same event processed twice should return 200 both times.
    """
    event_id = payload.get("id")
    if not event_id:
        return WebhookResult(status_code=400, body={"error": "missing event id"})

    if event_id in _idempotency_store:
        return WebhookResult(
            status_code=200,
            body={"status": "already_processed", "event_id": event_id},
        )

    _idempotency_store[event_id] = datetime.utcnow()
    return WebhookResult(
        status_code=200,
        body={"status": "processed", "event_id": event_id},
    )