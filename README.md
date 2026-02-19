# byteforge-aegis-client-python

Python client for the [ByteForge Aegis](https://github.com/jmazzahacks/byteforge-aegis) multi-tenant authentication service.

## Installation

```bash
pip install git+https://github.com/Really-Bad-Apps/byteforge-aegis-client-python.git
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

## License

[O'Saasy License](https://osaasy.dev/) - Copyright 2026, Really Bad Apps, LLC.
