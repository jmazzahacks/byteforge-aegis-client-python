from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AegisClientConfig:
    """
    Configuration for the Aegis API client.

    Attributes:
        api_url: Base URL of the authentication API (e.g., 'https://auth.example.com')
        site_id: Default site UUID for user operations
        master_api_key: Master API key for administrative operations
        tenant_api_key: Per-tenant secret sent as X-Tenant-Api-Key on public auth
            endpoints (register, login, password reset, etc.). Must live on the
            tenant's backend, never in browser-shipped code.
        auto_refresh: Enable automatic token refresh (default: True)
        refresh_buffer_seconds: Seconds before expiration to trigger proactive refresh (default: 300)
    """
    api_url: str
    site_id: Optional[str] = None
    # repr=False on both keys: the generated __repr__ would otherwise print
    # them verbatim, so anything that logs a config, or an unhandled
    # traceback with one in a local, writes live credentials into the
    # consumer's logs. Nothing in this library logs — but the consumer's
    # framework will, and by then the secret has already left.
    master_api_key: Optional[str] = field(default=None, repr=False)
    tenant_api_key: Optional[str] = field(default=None, repr=False)
    auto_refresh: bool = True
    refresh_buffer_seconds: int = 300
