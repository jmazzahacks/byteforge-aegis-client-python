# byteforge-aegis-client-python

Python client for the [ByteForge Aegis](https://github.com/jmazzahacks/byteforge-aegis) multi-tenant authentication service.

## Installation

```bash
pip install git+https://github.com/jmazzahacks/byteforge-aegis-client-python.git
```

## Quick Start

```python
from byteforge_aegis_client import AegisClient, AegisClientConfig, AegisApiError

client = AegisClient(AegisClientConfig(
    api_url="https://auth.example.com",
    site_id=1,
))

# Login - raises AegisApiError on failure
try:
    result = client.login("user@example.com", "password123")
    print(f"Logged in as user {result.auth_token.user_id}")
except AegisApiError as e:
    print(f"Login failed: {e.message}")

# Tokens are auto-managed after login
users = client.admin_list_users()
```

## Admin Operations

```python
from byteforge_aegis_client import AegisClient, AegisClientConfig, CreateSiteRequest

admin = AegisClient(AegisClientConfig(
    api_url="https://auth.example.com",
    master_api_key="your-master-key",
))

# List all sites
sites = admin.list_sites()

# Create a site
site = admin.create_site(CreateSiteRequest(
    name="My App",
    domain="myapp.com",
    frontend_url="https://myapp.com",
    email_from="noreply@myapp.com",
    email_from_name="My App",
))
```

## Webhook Signature Verification

When your application receives webhooks from Aegis, use `verify_webhook_signature` to confirm they are authentic:

```python
from flask import Flask, request, jsonify
from byteforge_aegis_client import verify_webhook_signature

WEBHOOK_SECRET = "your-site-webhook-secret"

app = Flask(__name__)

@app.post("/api/webhooks/aegis")
def handle_webhook():
    signature = request.headers.get("X-Aegis-Signature", "")
    timestamp = request.headers.get("X-Aegis-Timestamp", "")
    body = request.get_data(as_text=True)

    if not verify_webhook_signature(WEBHOOK_SECRET, signature, timestamp, body):
        return jsonify({"error": "Invalid signature"}), 401

    payload = request.get_json()
    if payload["event_type"] == "user.verified":
        print(f"User verified: {payload['email']}")

    return jsonify({"received": True}), 200
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `secret` | `str` | The webhook secret for this site |
| `signature_header` | `str` | Value of the `X-Aegis-Signature` header |
| `timestamp` | `str` | Value of the `X-Aegis-Timestamp` header |
| `body` | `str` | Raw request body string |
| `tolerance_seconds` | `int` | Max age in seconds (default 300, set to 0 to disable) |

The function uses constant-time comparison to prevent timing attacks and checks timestamp freshness to prevent replay attacks.

## License

[O'Saasy License](https://osaasy.dev/) - Copyright 2026, Really Bad Apps, LLC.
