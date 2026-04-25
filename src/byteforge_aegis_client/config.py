from dataclasses import dataclass
from typing import Optional


@dataclass
class AegisClientConfig:
    """
    Configuration for the Aegis API client.

    Attributes:
        api_url: Base URL of the authentication API (e.g., 'https://auth.example.com')
        site_id: Default site ID for user operations
        master_api_key: Master API key for administrative operations
        tenant_api_key: Per-tenant secret sent as X-Tenant-Api-Key on public auth
            endpoints (register, login, password reset, etc.). Must live on the
            tenant's backend, never in browser-shipped code.
        auto_refresh: Enable automatic token refresh (default: True)
        refresh_buffer_seconds: Seconds before expiration to trigger proactive refresh (default: 300)
    """
    api_url: str
    site_id: Optional[int] = None
    master_api_key: Optional[str] = None
    tenant_api_key: Optional[str] = None
    auto_refresh: bool = True
    refresh_buffer_seconds: int = 300
