"""
Tests for the tenant_api_key plumbing on AegisClient.

The client should attach the X-Tenant-Api-Key header automatically when
tenant_api_key is set in AegisClientConfig, and omit it otherwise.
"""
import responses

from byteforge_aegis_client import AegisClient

from conftest import API_URL


@responses.activate
def test_register_sends_tenant_api_key_header(tenant_client: AegisClient) -> None:
    """A client configured with tenant_api_key sends X-Tenant-Api-Key on register."""
    responses.add(
        responses.POST,
        f"{API_URL}/api/auth/register",
        json={"message": "Registration initiated. Please check your email to continue."},
        status=201,
    )

    tenant_client.register(email="new@test.com", password="testpass123")

    request = responses.calls[0].request
    assert request.headers.get("X-Tenant-Api-Key") == "tenant_secret_abc123"


@responses.activate
def test_login_sends_tenant_api_key_header(tenant_client: AegisClient) -> None:
    responses.add(
        responses.POST,
        f"{API_URL}/api/auth/login",
        json={
            "auth_token": {"token": "t", "user_id": 1, "expires_at": 9999999999},
            "refresh_token": None,
        },
        status=200,
    )

    tenant_client.login(email="new@test.com", password="pw")

    request = responses.calls[0].request
    assert request.headers.get("X-Tenant-Api-Key") == "tenant_secret_abc123"


@responses.activate
def test_request_password_reset_sends_tenant_api_key_header(tenant_client: AegisClient) -> None:
    responses.add(
        responses.POST,
        f"{API_URL}/api/auth/request-password-reset",
        json={"message": "ok"},
        status=200,
    )

    tenant_client.request_password_reset(email="new@test.com")

    request = responses.calls[0].request
    assert request.headers.get("X-Tenant-Api-Key") == "tenant_secret_abc123"


@responses.activate
def test_check_verification_token_includes_site_id_in_body(tenant_client: AegisClient) -> None:
    """check_verification_token now sends site_id in the body (sourced from config)."""
    import json
    responses.add(
        responses.POST,
        f"{API_URL}/api/auth/check-verification-token",
        json={"password_required": False, "email": "x@y.z"},
        status=200,
    )

    tenant_client.check_verification_token(token="vtoken")

    request = responses.calls[0].request
    body = json.loads(request.body)
    assert body["site_id"] == 1
    assert body["token"] == "vtoken"
    assert request.headers.get("X-Tenant-Api-Key") == "tenant_secret_abc123"


@responses.activate
def test_client_without_tenant_key_omits_header(client: AegisClient) -> None:
    """Default client without tenant_api_key in config sends no X-Tenant-Api-Key header."""
    responses.add(
        responses.POST,
        f"{API_URL}/api/auth/register",
        json={"message": "Registration initiated. Please check your email to continue."},
        status=201,
    )

    client.register(email="new@test.com", password="testpass123")

    request = responses.calls[0].request
    assert "X-Tenant-Api-Key" not in request.headers
