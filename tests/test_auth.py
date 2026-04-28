"""Tests for authentication methods."""
import pytest
import responses

from byteforge_aegis_client import AegisClient, AegisClientConfig, AegisApiError
from byteforge_aegis_models import LoginResult, MessageResponse

from conftest import API_URL, make_login_response_dict


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

        result = client.login("user@test.com", "password", site_id=5)
        body = responses.calls[0].request.body.decode()
        assert '"site_id": 5' in body


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
