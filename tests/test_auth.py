"""Tests for authentication methods."""
import pytest
import responses

from byteforge_aegis_client import AegisClient, AegisClientConfig, AegisApiError
from byteforge_aegis_models import LoginResult, MessageResponse, User

from conftest import API_URL, SITE_UUID, make_login_response_dict, make_user_dict


class TestLogin:
    @responses.activate
    def test_login_success(self, client: AegisClient) -> None:
        login_data = make_login_response_dict()
        responses.add(
            responses.POST, f"{API_URL}/api/auth/login",
            json=login_data, status=200,
        )

        result = client.login("user@test.com", "password123")

        assert isinstance(result, LoginResult)
        assert result.auth_token.token == "tok_abc"
        assert client.get_auth_token() == "tok_abc"
        assert client.get_refresh_token() == "ref_xyz"

    @responses.activate
    def test_login_invalid_credentials(self, client: AegisClient) -> None:
        responses.add(
            responses.POST, f"{API_URL}/api/auth/login",
            json={"error": "Invalid credentials"}, status=401,
        )

        with pytest.raises(AegisApiError) as exc_info:
            client.login("user@test.com", "wrong")
        assert exc_info.value.status_code == 401
        assert "Invalid credentials" in exc_info.value.message

    def test_login_no_site_id(self) -> None:
        client = AegisClient(AegisClientConfig(api_url=API_URL))
        with pytest.raises(ValueError, match="site_id"):
            client.login("user@test.com", "password")

    @responses.activate
    def test_login_with_explicit_site_id(self, client: AegisClient) -> None:
        responses.add(
            responses.POST, f"{API_URL}/api/auth/login",
            json=make_login_response_dict(), status=200,
        )

        other_site = "0191e1a0-0000-7000-8000-000000000005"
        result = client.login("user@test.com", "password", site_id=other_site)
        body = responses.calls[0].request.body.decode()
        assert f'"site_id": "{other_site}"' in body


class TestLogout:
    @responses.activate
    def test_logout_success(self, authed_client: AegisClient) -> None:
        responses.add(
            responses.POST, f"{API_URL}/api/auth/logout",
            json={"message": "Logged out successfully"}, status=200,
        )

        result = authed_client.logout()

        assert isinstance(result, MessageResponse)
        assert result.message == "Logged out successfully"
        assert authed_client.get_auth_token() is None
        assert authed_client.get_refresh_token() is None

    @responses.activate
    def test_logout_clears_tokens_on_error(self, authed_client: AegisClient) -> None:
        responses.add(
            responses.POST, f"{API_URL}/api/auth/logout",
            json={"error": "Token expired"}, status=401,
        )

        with pytest.raises(AegisApiError):
            authed_client.logout()
        assert authed_client.get_auth_token() is None

    def test_logout_no_token(self, client: AegisClient) -> None:
        with pytest.raises(ValueError, match="Authentication token"):
            client.logout()


class TestRegister:
    @responses.activate
    def test_register_success(self, client: AegisClient) -> None:
        responses.add(
            responses.POST, f"{API_URL}/api/auth/register",
            json={"message": "Registration initiated. Please check your email to continue."},
            status=201,
        )

        result = client.register("user@test.com", "password123")

        assert isinstance(result, MessageResponse)
        assert "Registration initiated" in result.message

    @responses.activate
    def test_register_without_password(self, client: AegisClient) -> None:
        responses.add(
            responses.POST, f"{API_URL}/api/auth/register",
            json={"message": "Registration initiated. Please check your email to continue."},
            status=201,
        )

        client.register("user@test.com")
        body = responses.calls[0].request.body.decode()
        assert "password" not in body


class TestInviteUser:
    """The tenant-key invite path.

    Distinct from register in the two ways that made register unusable for
    invitations: it returns the created User, and a duplicate is a real
    error rather than an indistinguishable success.
    """

    @responses.activate
    def test_success(self, tenant_client: AegisClient) -> None:
        responses.add(
            responses.POST, f"{API_URL}/api/auth/invite-user",
            json=make_user_dict(), status=201,
        )

        user = tenant_client.invite_user("invitee@test.com")

        assert isinstance(user, User)

    @responses.activate
    def test_sends_the_tenant_key(self, tenant_client: AegisClient) -> None:
        """The only credential this endpoint takes."""
        responses.add(
            responses.POST, f"{API_URL}/api/auth/invite-user",
            json=make_user_dict(), status=201,
        )

        tenant_client.invite_user("invitee@test.com")

        assert responses.calls[0].request.headers["X-Tenant-Api-Key"] == "tenant_secret_abc123"

    @responses.activate
    def test_sends_site_id_and_never_a_role(self, tenant_client: AegisClient) -> None:
        """site_id is what the tenant-key gate authenticates against, and
        role is absent by design — a tenant key must not mint admins."""
        responses.add(
            responses.POST, f"{API_URL}/api/auth/invite-user",
            json=make_user_dict(), status=201,
        )

        tenant_client.invite_user("invitee@test.com")

        body = responses.calls[0].request.body.decode()
        assert SITE_UUID in body
        assert "role" not in body
        assert "password" not in body

    @responses.activate
    def test_duplicate_email_raises(self, tenant_client: AegisClient) -> None:
        """The difference from register that matters: the caller can tell."""
        responses.add(
            responses.POST, f"{API_URL}/api/auth/invite-user",
            json={"error": "Email already registered for this site"}, status=400,
        )

        with pytest.raises(AegisApiError):
            tenant_client.invite_user("taken@test.com")

    def test_requires_a_site_id(self, admin_client: AegisClient) -> None:
        """admin_client has no site_id configured."""
        with pytest.raises(ValueError, match="site_id"):
            admin_client.invite_user("invitee@test.com")


class TestRefresh:
    @responses.activate
    def test_refresh_success(self, client: AegisClient) -> None:
        client.set_refresh_token("old_refresh")
        responses.add(
            responses.POST, f"{API_URL}/api/auth/refresh",
            json=make_login_response_dict(auth_token="new_auth", refresh_token="new_refresh"),
            status=200,
        )

        result = client.refresh_auth_token()

        assert isinstance(result, LoginResult)
        assert client.get_auth_token() == "new_auth"
        assert client.get_refresh_token() == "new_refresh"

    def test_refresh_no_token(self, client: AegisClient) -> None:
        with pytest.raises(ValueError, match="No refresh token"):
            client.refresh_auth_token()
