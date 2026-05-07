"""
Tests for AegisClient.get_user — tenant-key-gated single-user lookup.
"""
import responses

from byteforge_aegis_client import AegisClient

from conftest import API_URL, make_user_dict


@responses.activate
def test_get_user_hits_path_endpoint_with_tenant_key(tenant_client: AegisClient) -> None:
    """get_user calls /api/sites/{site_id}/users/{user_id} with X-Tenant-Api-Key."""
    responses.add(
        responses.GET,
        f"{API_URL}/api/sites/1/users/42",
        json=make_user_dict(user_id=42, role="admin"),
        status=200,
    )

    user = tenant_client.get_user(user_id=42)

    request = responses.calls[0].request
    assert request.headers.get("X-Tenant-Api-Key") == "tenant_secret_abc123"
    assert user.id == 42
    assert user.site_id == 1
    assert user.role.value == "admin"


@responses.activate
def test_get_user_with_explicit_site_id(tenant_client: AegisClient) -> None:
    """Explicit site_id arg overrides config.site_id."""
    responses.add(
        responses.GET,
        f"{API_URL}/api/sites/7/users/42",
        json=make_user_dict(user_id=42, site_id=7),
        status=200,
    )

    user = tenant_client.get_user(user_id=42, site_id=7)

    assert user.site_id == 7


@responses.activate
def test_get_user_without_tenant_key_omits_header(client: AegisClient) -> None:
    """Without tenant_api_key configured, the header is not attached.

    Backend would return 401 in real life — we don't enforce that on the
    client side, just that the header isn't accidentally injected.
    """
    responses.add(
        responses.GET,
        f"{API_URL}/api/sites/1/users/42",
        json=make_user_dict(user_id=42),
        status=200,
    )

    client.get_user(user_id=42)

    request = responses.calls[0].request
    assert "X-Tenant-Api-Key" not in request.headers
