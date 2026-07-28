"""Webhook signature verification for ByteForge Aegis webhooks."""
import hashlib
import hmac
import re
import time


# A SHA-256 HMAC rendered as hex. Signature headers are matched against this
# before comparison: hmac.compare_digest raises TypeError on non-ASCII str,
# and header values arrive latin-1-decoded, so an unauthenticated caller
# could otherwise crash a receiver with a single high byte.
_HEX_DIGEST = re.compile(r'[0-9a-fA-F]{64}')


def verify_webhook_signature(
    secret: str,
    signature_header: str,
    timestamp: str,
    body: str,
    tolerance_seconds: int = 300,
) -> bool:
    """
    Verify an incoming Aegis webhook signature.

    Aegis signs webhooks with HMAC-SHA256 over "{timestamp}.{body}" and sends
    the result in the X-Aegis-Signature header as "sha256={hex_digest}".

    Args:
        secret: The webhook secret for this site (from site.webhook_secret).
        signature_header: The value of the X-Aegis-Signature header.
        timestamp: The value of the X-Aegis-Timestamp header.
        body: The raw request body string.
        tolerance_seconds: Maximum age of the webhook in seconds (default 300).
            Set to 0 to disable timestamp freshness checking.

    Returns:
        True if the signature is valid (and timestamp is fresh), False otherwise.
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

    return hmac.compare_digest(expected_digest, received_digest)
