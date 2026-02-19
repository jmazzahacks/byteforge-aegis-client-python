"""Python client for ByteForge Aegis multi-tenant authentication."""

__version__ = "1.0.0"

from byteforge_aegis_client.aegis_client import AegisClient
from byteforge_aegis_client.config import AegisClientConfig
from byteforge_aegis_client.exceptions import AegisApiError, AegisError, AegisNetworkError
from byteforge_aegis_client.request_models import CreateSiteRequest, UpdateSiteRequest

__all__ = [
    "AegisClient",
    "AegisClientConfig",
    "AegisApiError",
    "AegisError",
    "AegisNetworkError",
    "CreateSiteRequest",
    "UpdateSiteRequest",
]
