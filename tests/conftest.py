"""Shared fixtures for client tests."""
import pytest
import responses

from byteforge_aegis_client import AegisClient, AegisClientConfig

API_URL = "https://auth.test.example.com"


@pytest.fixture
def client() -> AegisClient:
    """Client configured with site_id for user operations."""
    return AegisClient(AegisClientConfig(
        api_url=API_URL,
        site_id=1,
        auto_refresh=False,
    ))


@pytest.fixture
def admin_client() -> AegisClient:
    """Client configured with master API key for admin operations."""
    return AegisClient(AegisClientConfig(
        api_url=API_URL,
        master_api_key="master_key_123",
        auto_refresh=False,
    ))


@pytest.fixture
def authed_client() -> AegisClient:
    """Client with an auth token already set."""
    c = AegisClient(AegisClientConfig(
        api_url=API_URL,
        site_id=1,
        auto_refresh=False,
    ))
    c.set_auth_token("test_auth_token")
    return c


@pytest.fixture
def tenant_client() -> AegisClient:
    """Client configured with both site_id and tenant_api_key."""
    return AegisClient(AegisClientConfig(
        api_url=API_URL,
        site_id=1,
        tenant_api_key="tenant_secret_abc123",
        auto_refresh=False,
    ))


def make_user_dict(
    user_id: int = 10,
    site_id: int = 1,
    email: str = "user@test.com",
    is_verified: bool = True,
    role: str = "user",
) -> dict:
    """Helper to build a user response dict."""
    return {
        "id": user_id,
        "site_id": site_id,
        "email": email,
        "is_verified": is_verified,
        "role": role,
        "created_at": 1700000000,
        "updated_at": 1700000100,
    }


def make_login_response_dict(
    auth_token: str = "tok_abc",
    refresh_token: str = "ref_xyz",
    user_id: int = 10,
    expires_at: int = 1700099999,
) -> dict:
    """Helper to build a login response dict."""
    return {
        "auth_token": {
            "token": auth_token,
            "user_id": user_id,
            "expires_at": expires_at,
        },
        "refresh_token": {
            "token": refresh_token,
            "site_id": 1,
            "user_id": user_id,
            "family_id": "fam_123",
            "expires_at": expires_at + 86400,
            "created_at": 1700000000,
        },
    }


def make_site_dict(site_id: int = 1) -> dict:
    """Helper to build a site response dict."""
    return {
        "id": site_id,
        "name": "Test Site",
        "domain": "test.example.com",
        "frontend_url": "https://test.example.com",
        "email_from": "noreply@test.example.com",
        "email_from_name": "Test Site",
        "created_at": 1700000000,
        "updated_at": 1700000100,
    }
