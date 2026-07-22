"""Tests for admin methods."""
import pytest
import responses

from byteforge_aegis_client import AegisClient, AegisApiError
from byteforge_aegis_models import HealthStatus, Site, User

from conftest import API_URL, SITE_UUID, USER_UUID, make_site_dict, make_user_dict

OTHER_USER_UUID = "0191e1a0-0000-7000-8000-0000000000bb"
UNKNOWN_USER_UUID = "0191e1a0-0000-7000-8000-0000000fffff"


class TestHealthCheck:
    @responses.activate
    def test_success(self, client: AegisClient) -> None:
        responses.add(
            responses.GET, f"{API_URL}/api/health",
            json={"status": "ok"}, status=200,
        )

        result = client.health_check()
        assert isinstance(result, HealthStatus)
        assert result.status == "ok"


class TestAdminListUsers:
    @responses.activate
    def test_success(self, authed_client: AegisClient) -> None:
        responses.add(
            responses.GET, f"{API_URL}/api/admin/users",
            json=[make_user_dict(), make_user_dict(user_uuid=OTHER_USER_UUID)],
            status=200,
        )

        users = authed_client.admin_list_users()
        assert len(users) == 2
        assert all(isinstance(u, User) for u in users)

    def test_no_auth_token(self, client: AegisClient) -> None:
        with pytest.raises(ValueError, match="Authentication token"):
            client.admin_list_users()


class TestRegisterAdmin:
    @responses.activate
    def test_success(self, admin_client: AegisClient) -> None:
        responses.add(
            responses.POST, f"{API_URL}/api/admin/register",
            json=make_user_dict(role="admin"), status=201,
        )

        user = admin_client.register_admin("admin@test.com", site_id=SITE_UUID, role="admin")
        assert isinstance(user, User)
        assert user.role.value == "admin"


class TestAegisAdminListSites:
    @responses.activate
    def test_success(self, client: AegisClient) -> None:
        responses.add(
            responses.GET, f"{API_URL}/api/sites",
            json=[make_site_dict()], status=200,
        )

        sites = client.aegis_admin_list_sites("admin_bearer_token")

        assert len(sites) == 1
        assert isinstance(sites[0], Site)
        assert responses.calls[0].request.headers["Authorization"] == "Bearer admin_bearer_token"
        # Original token should be restored
        assert client.get_auth_token() is None

    @responses.activate
    def test_preserves_existing_token(self, authed_client: AegisClient) -> None:
        responses.add(
            responses.GET, f"{API_URL}/api/sites",
            json=[make_site_dict()], status=200,
        )

        authed_client.aegis_admin_list_sites("temp_admin_token")
        assert authed_client.get_auth_token() == "test_auth_token"


class TestAegisAdminListUsersBySite:
    @responses.activate
    def test_success(self, client: AegisClient) -> None:
        responses.add(
            responses.GET, f"{API_URL}/api/sites/{SITE_UUID}/users",
            json=[make_user_dict()], status=200,
        )

        users = client.aegis_admin_list_users_by_site(SITE_UUID, "admin_token")

        assert len(users) == 1
        assert isinstance(users[0], User)


class TestDeleteUser:
    @responses.activate
    def test_success(self, admin_client: AegisClient) -> None:
        responses.add(
            responses.DELETE, f"{API_URL}/api/admin/users/{USER_UUID}",
            json={"message": "User deleted successfully"}, status=200,
        )

        result = admin_client.delete_user(USER_UUID)

        assert result is None
        assert responses.calls[0].request.headers["X-API-Key"] == "master_key_123"

    @responses.activate
    def test_not_found(self, admin_client: AegisClient) -> None:
        responses.add(
            responses.DELETE, f"{API_URL}/api/admin/users/{UNKNOWN_USER_UUID}",
            json={"error": "User not found"}, status=404,
        )

        with pytest.raises(AegisApiError) as exc_info:
            admin_client.delete_user(UNKNOWN_USER_UUID)
        assert exc_info.value.status_code == 404

    def test_no_api_key(self, client: AegisClient) -> None:
        with pytest.raises(ValueError, match="Master API key"):
            client.delete_user(USER_UUID)
