"""Tests for webhook signature verification."""
import hashlib
import hmac
import time

from byteforge_aegis_client import verify_webhook_signature

SECRET = "test_webhook_secret_abc123"
BODY = '{"event_type":"user.verified","site_uuid":"0191e1a0-0000-7000-8000-000000000001","user_uuid":"0191e1a0-0000-7000-8000-0000000000aa","email":"u@test.com","aegis_role":"user","timestamp":1700000000}'


def _make_signature(secret: str, timestamp: str, body: str) -> str:
    """Compute signature the same way the Aegis backend does."""
    message = f"{timestamp}.{body}"
    digest = hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def test_valid_signature():
    ts = str(int(time.time()))
    sig = _make_signature(SECRET, ts, BODY)

    assert verify_webhook_signature(SECRET, sig, ts, BODY) is True


def test_wrong_secret_fails():
    ts = str(int(time.time()))
    sig = _make_signature(SECRET, ts, BODY)

    assert verify_webhook_signature("wrong_secret", sig, ts, BODY) is False


def test_tampered_body_fails():
    ts = str(int(time.time()))
    sig = _make_signature(SECRET, ts, BODY)

    assert verify_webhook_signature(SECRET, sig, ts, BODY + "x") is False


def test_stale_timestamp_fails():
    old_ts = str(int(time.time()) - 600)  # 10 minutes ago
    sig = _make_signature(SECRET, old_ts, BODY)

    assert verify_webhook_signature(SECRET, sig, old_ts, BODY, tolerance_seconds=300) is False


def test_tolerance_zero_disables_freshness_check():
    old_ts = str(int(time.time()) - 99999)
    sig = _make_signature(SECRET, old_ts, BODY)

    assert verify_webhook_signature(SECRET, sig, old_ts, BODY, tolerance_seconds=0) is True


def test_malformed_signature_header_fails():
    ts = str(int(time.time()))

    assert verify_webhook_signature(SECRET, "", ts, BODY) is False
    assert verify_webhook_signature(SECRET, "bad_format", ts, BODY) is False
    assert verify_webhook_signature(SECRET, "md5=abc123", ts, BODY) is False


def test_invalid_timestamp_fails():
    sig = _make_signature(SECRET, "not_a_number", BODY)

    assert verify_webhook_signature(SECRET, sig, "not_a_number", BODY) is False


def test_future_timestamp_within_tolerance_passes():
    future_ts = str(int(time.time()) + 60)  # 1 minute in future
    sig = _make_signature(SECRET, future_ts, BODY)

    assert verify_webhook_signature(SECRET, sig, future_ts, BODY, tolerance_seconds=300) is True


def test_future_timestamp_outside_tolerance_fails():
    future_ts = str(int(time.time()) + 600)  # 10 minutes in future
    sig = _make_signature(SECRET, future_ts, BODY)

    assert verify_webhook_signature(SECRET, sig, future_ts, BODY, tolerance_seconds=300) is False


def test_non_ascii_signature_is_rejected_not_raised() -> None:
    """Unauthenticated callers must not be able to crash a receiver.

    X-Aegis-Signature is attacker-controlled and needs no captured delivery.
    hmac.compare_digest raises TypeError on non-ASCII str, and header values
    arrive latin-1-decoded, so a single high byte would 500 the handler.
    """
    ts = str(int(time.time()))
    assert verify_webhook_signature(SECRET, "sha256=" + "ÿ" * 64, ts, BODY) is False


def test_malformed_signature_is_rejected() -> None:
    ts = str(int(time.time()))
    for bad in ["sha256=", "sha256=xyz", "sha256=" + "a" * 63, "sha256=" + "a" * 65]:
        assert verify_webhook_signature(SECRET, bad, ts, BODY) is False, bad


# --- Unsigned X-Aegis-Event header -----------------------------------------
#
# The HMAC covers only "{timestamp}.{raw_body}". The X-Aegis-Event header is
# not signed, so a captured delivery can be replayed inside the freshness
# window with that header rewritten to any event. A receiver dispatching on
# the header then acts on a forged event. Passing event_type makes this
# function reject the mismatch.

def test_matching_event_header_passes():
    ts = str(int(time.time()))
    sig = _make_signature(SECRET, ts, BODY)

    assert verify_webhook_signature(
        SECRET, sig, ts, BODY, event_type="user.verified"
    ) is True


def test_rewritten_event_header_is_rejected():
    """The attack: a valid signature over a user.verified body, replayed
    with the header claiming user.deleted."""
    ts = str(int(time.time()))
    sig = _make_signature(SECRET, ts, BODY)

    assert verify_webhook_signature(
        SECRET, sig, ts, BODY, event_type="user.deleted"
    ) is False


def test_event_header_check_is_opt_in():
    """Omitting event_type preserves the old behaviour for existing callers."""
    ts = str(int(time.time()))
    sig = _make_signature(SECRET, ts, BODY)

    assert verify_webhook_signature(SECRET, sig, ts, BODY) is True


def test_non_json_body_with_event_type_is_rejected():
    ts = str(int(time.time()))
    body = "not json at all"
    sig = _make_signature(SECRET, ts, body)

    assert verify_webhook_signature(
        SECRET, sig, ts, body, event_type="user.verified"
    ) is False


def test_json_array_body_with_event_type_is_rejected():
    """A non-object body cannot agree with the header."""
    ts = str(int(time.time()))
    body = '["user.verified"]'
    sig = _make_signature(SECRET, ts, body)

    assert verify_webhook_signature(
        SECRET, sig, ts, body, event_type="user.verified"
    ) is False


def test_body_without_event_type_is_rejected():
    ts = str(int(time.time()))
    body = '{"user_uuid":"abc"}'
    sig = _make_signature(SECRET, ts, body)

    assert verify_webhook_signature(
        SECRET, sig, ts, body, event_type="user.verified"
    ) is False
