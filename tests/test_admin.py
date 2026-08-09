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


class TestAdminRegisterUser:
    """The bearer-token add-user endpoint the Aegis console itself uses.

    Distinct from register_admin below, which needs the master key. The
    site is never sent — Aegis derives it from the token's user record,
    which is what keeps an admin confined to their own site.
    """

    @responses.activate
    def test_success(self, authed_client: AegisClient) -> None:
        responses.add(
            responses.POST, f"{API_URL}/api/admin/register-user",
            json=make_user_dict(), status=201,
        )

        user = authed_client.admin_register_user("invitee@test.com")
        assert isinstance(user, User)

    @responses.activate
    def test_omits_role_when_not_given(self, authed_client: AegisClient) -> None:
        responses.add(
            responses.POST, f"{API_URL}/api/admin/register-user",
            json=make_user_dict(), status=201,
        )

        authed_client.admin_register_user("invitee@test.com")

        body = responses.calls[0].request.body
        assert b'"role"' not in body, "an absent role must let Aegis default it"
        assert b'"site_id"' not in body, "the site comes from the token, never the body"

    @responses.activate
    def test_sends_role_when_given(self, authed_client: AegisClient) -> None:
        responses.add(
            responses.POST, f"{API_URL}/api/admin/register-user",
            json=make_user_dict(role="admin"), status=201,
        )

        user = authed_client.admin_register_user("boss@test.com", role="admin")
        assert user.role.value == "admin"
        assert b'"role": "admin"' in responses.calls[0].request.body

    @responses.activate
    def test_duplicate_email_is_an_error(self, authed_client: AegisClient) -> None:
        """Unlike public register, this endpoint is not enumeration-safe —
        callers get a real 400 they can act on."""
        responses.add(
            responses.POST, f"{API_URL}/api/admin/register-user",
            json={"error": "Email already registered for this site"}, status=400,
        )

        with pytest.raises(AegisApiError):
            authed_client.admin_register_user("taken@test.com")

    def test_no_auth_token(self, client: AegisClient) -> None:
        with pytest.raises(ValueError, match="Authentication token"):
            client.admin_register_user("invitee@test.com")


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

    @responses.activate
    def test_protected_user_raises_409(self, admin_client: AegisClient) -> None:
        responses.add(
            responses.DELETE, f"{API_URL}/api/admin/users/{USER_UUID}",
            json={"error": "User is protected from deletion",
                  "code": "user_deletion_protected"}, status=409,
        )

        with pytest.raises(AegisApiError) as exc_info:
            admin_client.delete_user(USER_UUID)
        assert exc_info.value.status_code == 409


class TestSetUserDeletionProtection:
    @responses.activate
    def test_sets_flag(self, admin_client: AegisClient) -> None:
        responses.add(
            responses.PATCH, f"{API_URL}/api/admin/users/{USER_UUID}",
            json=make_user_dict(deletion_protected=True), status=200,
        )

        user = admin_client.set_user_deletion_protection(USER_UUID, True)

        assert isinstance(user, User)
        assert user.deletion_protected is True
        assert responses.calls[0].request.headers["X-API-Key"] == "master_key_123"
        assert b'"deletion_protected": true' in responses.calls[0].request.body

    @responses.activate
    def test_clears_flag(self, admin_client: AegisClient) -> None:
        responses.add(
            responses.PATCH, f"{API_URL}/api/admin/users/{USER_UUID}",
            json=make_user_dict(deletion_protected=False), status=200,
        )

        user = admin_client.set_user_deletion_protection(USER_UUID, False)

        assert user.deletion_protected is False
        assert b'"deletion_protected": false' in responses.calls[0].request.body

    @responses.activate
    def test_not_found(self, admin_client: AegisClient) -> None:
        responses.add(
            responses.PATCH, f"{API_URL}/api/admin/users/{UNKNOWN_USER_UUID}",
            json={"error": "User not found"}, status=404,
        )

        with pytest.raises(AegisApiError) as exc_info:
            admin_client.set_user_deletion_protection(UNKNOWN_USER_UUID, True)
        assert exc_info.value.status_code == 404

    def test_no_api_key(self, client: AegisClient) -> None:
        with pytest.raises(ValueError, match="Master API key"):
            client.set_user_deletion_protection(USER_UUID, True)
