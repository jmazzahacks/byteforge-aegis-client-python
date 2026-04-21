"""Python client for ByteForge Aegis multi-tenant authentication."""

__version__ = "1.2.0"

from byteforge_aegis_client.aegis_client import AegisClient
from byteforge_aegis_client.config import AegisClientConfig
from byteforge_aegis_client.exceptions import (
    AegisApiError,
    AegisError,
    AegisNetworkError,
    AegisUnauthorized,
)
from byteforge_aegis_client.request_models import CreateSiteRequest, UpdateSiteRequest
from byteforge_aegis_client.webhooks import verify_webhook_signature

__all__ = [
    "AegisClient",
    "AegisClientConfig",
    "AegisApiError",
    "AegisError",
    "AegisNetworkError",
    "AegisUnauthorized",
    "CreateSiteRequest",
    "UpdateSiteRequest",
    "verify_webhook_signature",
]
