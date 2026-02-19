"""Tests for password methods."""
import pytest
import responses

from byteforge_aegis_client import AegisClient, AegisApiError
from byteforge_aegis_models import MessageResponse, User

from conftest import API_URL, make_user_dict


class TestChangePassword:
    @responses.activate
    def test_success(self, authed_client: AegisClient) -> None:
        responses.add(
            responses.POST, f"{API_URL}/api/auth/change-password",
            json=make_user_dict(), status=200,
        )

        result = authed_client.change_password("old_pass", "new_pass")
        assert isinstance(result, User)

    def test_no_auth_token(self, client: AegisClient) -> None:
        with pytest.raises(ValueError, match="Authentication token"):
            client.change_password("old", "new")


class TestRequestPasswordReset:
    @responses.activate
    def test_success(self, client: AegisClient) -> None:
        responses.add(
            responses.POST, f"{API_URL}/api/auth/request-password-reset",
            json={"message": "Password reset email sent"}, status=200,
        )

        result = client.request_password_reset("user@test.com")
        assert isinstance(result, MessageResponse)
        assert "reset" in result.message.lower()


class TestResetPassword:
    @responses.activate
    def test_success(self, client: AegisClient) -> None:
        responses.add(
            responses.POST, f"{API_URL}/api/auth/reset-password",
            json=make_user_dict(), status=200,
        )

        result = client.reset_password("tok_reset_123", "new_password")
        assert isinstance(result, User)

    @responses.activate
    def test_invalid_token(self, client: AegisClient) -> None:
        responses.add(
            responses.POST, f"{API_URL}/api/auth/reset-password",
            json={"error": "Invalid or expired token"}, status=400,
        )

        with pytest.raises(AegisApiError) as exc_info:
            client.reset_password("bad_token", "new_password")
        assert exc_info.value.status_code == 400
