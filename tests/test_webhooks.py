"""Tests for webhook signature verification."""
import hashlib
import hmac
import time

from byteforge_aegis_client import verify_webhook_signature

SECRET = "test_webhook_secret_abc123"
BODY = '{"event_type":"user.verified","site_id":1,"user_id":10,"email":"u@test.com","aegis_role":"user","timestamp":1700000000}'


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
