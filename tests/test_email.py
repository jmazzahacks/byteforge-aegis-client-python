"""Tests for email change methods."""
import pytest
import responses

from byteforge_aegis_client import AegisClient
from byteforge_aegis_models import EmailChangeResponse, User

from conftest import API_URL, make_user_dict


class TestRequestEmailChange:
    @responses.activate
    def test_success(self, authed_client: AegisClient) -> None:
        responses.add(
            responses.POST, f"{API_URL}/api/auth/request-email-change",
            json={"message": "Verification email sent", "token": "tok_email_123"},
            status=200,
        )

        result = authed_client.request_email_change("new@test.com")

        assert isinstance(result, EmailChangeResponse)
        assert result.token == "tok_email_123"
        assert "sent" in result.message.lower()

    def test_no_auth_token(self, client: AegisClient) -> None:
        with pytest.raises(ValueError, match="Authentication token"):
            client.request_email_change("new@test.com")


class TestConfirmEmailChange:
    @responses.activate
    def test_success(self, client: AegisClient) -> None:
        responses.add(
            responses.POST, f"{API_URL}/api/auth/confirm-email-change",
            json=make_user_dict(email="new@test.com"), status=200,
        )

        result = client.confirm_email_change("tok_email_123")

        assert isinstance(result, User)
        assert result.email == "new@test.com"
