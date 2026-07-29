"""Webhook signature verification for ByteForge Aegis webhooks."""
import hashlib
import hmac
import json
import re
import time
from typing import Optional


# A SHA-256 HMAC rendered as hex. Signature headers are matched against this
# before comparison: hmac.compare_digest raises TypeError on non-ASCII str,
# and header values arrive latin-1-decoded, so an unauthenticated caller
# could otherwise crash a receiver with a single high byte.
_HEX_DIGEST = re.compile(r'[0-9a-fA-F]{64}')


def _header_matches_body(header_event_type: str, body: str) -> bool:
    """
    Whether the routing header agrees with the signed body.

    A body that is not JSON, not an object, or carries no event_type cannot
    agree with anything, so it is rejected rather than waved through.
    """
    try:
        payload = json.loads(body)
    except (ValueError, TypeError):
        return False

    if not isinstance(payload, dict):
        return False

    return payload.get('event_type') == header_event_type


def verify_webhook_signature(
    secret: str,
    signature_header: str,
    timestamp: str,
    body: str,
    tolerance_seconds: int = 300,
    event_type: Optional[str] = None,
) -> bool:
    """
    Verify an incoming Aegis webhook signature.

    Aegis signs webhooks with HMAC-SHA256 over "{timestamp}.{body}" and sends
    the result in the X-Aegis-Signature header as "sha256={hex_digest}".

    IMPORTANT — pass event_type. The signature covers only the timestamp and
    the body. The X-Aegis-Event header is NOT signed, so anyone holding a
    captured delivery for your site can replay it within the freshness
    window with that header rewritten to any event they like, and the
    signature still verifies. If you dispatch on the header — which is the
    natural thing to do — that is a forged event your handler will act on.

    Supplying event_type makes this function reject any delivery whose
    header disagrees with the signed body. Omitting it leaves the check off,
    for backwards compatibility only.

    Args:
        secret: The webhook secret for this site (from site.webhook_secret).
        signature_header: The value of the X-Aegis-Signature header.
        timestamp: The value of the X-Aegis-Timestamp header.
        body: The raw request body string.
        tolerance_seconds: Maximum age of the webhook in seconds (default 300).
            Set to 0 to disable timestamp freshness checking.
        event_type: The value of the X-Aegis-Event header. When supplied,
            verification fails unless it matches the signed body's
            event_type. Strongly recommended.

    Returns:
        True if the signature is valid (and timestamp is fresh, and the
        event header agrees with the body when supplied), False otherwise.
    """
    if not signature_header or not signature_header.startswith("sha256="):
        return False

    received_digest = signature_header[7:]

    # Reject anything that isn't a hex digest before comparing. Without this,
    # a non-ASCII byte in the attacker-controlled X-Aegis-Signature header
    # makes hmac.compare_digest raise TypeError — an unauthenticated 500 on
    # any receiver, no captured delivery required.
    if not _HEX_DIGEST.fullmatch(received_digest):
        return False

    # Check timestamp freshness
    if tolerance_seconds > 0:
        try:
            webhook_time = int(timestamp)
        except (ValueError, TypeError):
            return False

        current_time = int(time.time())
        if abs(current_time - webhook_time) > tolerance_seconds:
            return False

    # Compute expected signature
    message = f"{timestamp}.{body}"
    expected_digest = hmac.new(
        secret.encode(),
        message.encode(),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected_digest, received_digest):
        return False

    if event_type is None:
        return True

    return _header_matches_body(event_type, body)
