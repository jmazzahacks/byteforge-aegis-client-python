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
    site_id="0191e1a0-5e2f-7c3a-9d4b-1f2e3a4b5c6d",  # your site's UUID
))

# Login - raises AegisApiError on failure
try:
    result = client.login("user@example.com", "password123")
    print(f"Logged in as user {result.auth_token.user_uuid}")
except AegisApiError as e:
    print(f"Login failed: {e.message}")

# Tokens are auto-managed after login
users = client.admin_list_users()

# Add a user to your own site (requires an admin-role bearer token).
# The site is derived from the token, so there is no site_id to pass.
# The invitee gets a verification email and sets their own password.
new_user = client.admin_register_user("invitee@example.com")
```

## Inviting users (tenant API key)

If you are an integrating backend adding users to your own site, this is the
path you want. It needs only the tenant API key you already hold — no bearer
token, no master key.

```python
from byteforge_aegis_client import AegisClient, AegisClientConfig, AegisApiError

client = AegisClient(AegisClientConfig(
    api_url="https://auth.example.com",
    site_id="0191e1a0-5e2f-7c3a-9d4b-1f2e3a4b5c6d",
    tenant_api_key="your-tenant-key",   # server-side only, never in the browser
))

try:
    user = client.invite_user("invitee@example.com")
except AegisApiError as e:
    if e.status_code == 400:
        ...  # already an established user on this site
```

Re-inviting someone who has not accepted yet resends the link, invalidates the
previous one, and returns the same user. Verification links expire after 24h
while the account does not, so without that an ignored or spam-filtered
invitation would block every retry and lock the invitee out for good. Accounts
anyone has begun using are never resent to.

You authorize the invitation yourself, against your own session and your own
rules, before calling. Aegis only checks that the key belongs to the site
named — and a tenant key can never name another site.

The invitee is created **without a password** and emailed a link to *your*
frontend (`{frontend_url}/verify-email?token=…`, valid 24h). Your page calls
`check_verification_token(token)` to learn that `password_required` is true,
collects a password, and calls `verify_email(token, password)`. All three
calls use the same tenant key.

### Why not `register(password=None)`?

`register` is the public signup path and it differs in two ways that matter
for invitations:

| | `invite_user` | `register` |
|---|---|---|
| Site must allow self-registration | no | **yes** |
| Established duplicate | raises 400 | silent 201, creates nothing |
| Pending invitation | resends the link | silent 201, creates nothing |
| Returns | the created `User` | a generic `MessageResponse` |
| Can set a role | no, always an ordinary user | no |

`register` is enumeration-safe on purpose — it must not reveal to a stranger
at a signup form whether an address is registered. That protects nothing when
the caller already owns the site's entire user list, and it costs you the
ability to tell whether the invite landed.

### `user.verified` is your only signal

No webhook fires when you invite. `user.verified` fires when the invitee sets
their password, and that event *is* proof they control the mailbox: the
verification token is only ever delivered by email and appears in no API
response. Binding an account or a membership on it is sound.

An invitation that is never accepted produces no event at all — **expire your
own pending invites** rather than waiting.

## Admin Operations

```python
from byteforge_aegis_client import AegisClient, AegisClientConfig, CreateSiteRequest, UpdateSiteRequest

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

# Protect an ENTIRE TENANT from user deletion. Once set, no user on this
# site can be deleted (409 'site_deletion_protected') and the site itself
# cannot be deleted. Prefer this when every account on the tenant anchors
# unrecoverable records — it does not depend on remembering to mark each user.
site = admin.update_site(site_uuid, UpdateSiteRequest(deletion_protected=True))
assert site.deletion_protected

# Protect a user from deletion — delete_user then raises AegisApiError with
# status 409 and code 'user_deletion_protected'. Use for accounts whose
# records hold value that would be unattributable without the Aegis identity.
user = admin.set_user_deletion_protection(user_uuid, True)
assert user.deletion_protected
```

## Webhook Signature Verification

When your application receives webhooks from Aegis, use `verify_webhook_signature` to confirm they are authentic:

```python
from flask import Flask, request, jsonify
from byteforge_aegis_client import WebhookEventType, verify_webhook_signature

WEBHOOK_SECRET = "your-site-webhook-secret"

app = Flask(__name__)

@app.post("/api/webhooks/aegis")
def handle_webhook():
    signature = request.headers.get("X-Aegis-Signature", "")
    timestamp = request.headers.get("X-Aegis-Timestamp", "")
    event_type = request.headers.get("X-Aegis-Event", "")
    body = request.get_data(as_text=True)

    # Pass event_type. The HMAC covers only "{timestamp}.{raw_body}", so the
    # X-Aegis-Event header is NOT signed — without this argument a captured
    # delivery can be replayed inside the freshness window with that header
    # rewritten to any event, and the signature still verifies.
    if not verify_webhook_signature(
        WEBHOOK_SECRET, signature, timestamp, body, event_type=event_type
    ):
        return jsonify({"error": "Invalid signature"}), 401

    payload = request.get_json()
    # Dispatch on the BODY's event_type. The HMAC covers only
    # "{timestamp}.{raw_body}", so the X-Aegis-Event header is NOT signed —
    # a captured delivery replayed inside the freshness window with that
    # header rewritten still verifies. The body is the authoritative value.
    if payload["event_type"] == WebhookEventType.USER_VERIFIED:
        print(f"User verified: {payload['email']}")
    elif payload["event_type"] == WebhookEventType.USER_DELETED:
        print(f"User deleted: {payload['user_uuid']}")

    return jsonify({"received": True}), 200
```

`WebhookEventType` is a `str`-subclass enum, so its members compare equal to the raw strings on the wire (`"user.verified"`, `"user.deleted"`) — plain string comparison keeps working too.

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
