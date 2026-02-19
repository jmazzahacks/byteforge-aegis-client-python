"""Tests for verification methods."""
import responses

from byteforge_aegis_client import AegisClient
from byteforge_aegis_models import VerificationResult, VerificationTokenStatus

from conftest import API_URL, make_user_dict


class TestCheckVerificationToken:
    @responses.activate
    def test_success(self, client: AegisClient) -> None:
        responses.add(
            responses.POST, f"{API_URL}/api/auth/check-verification-token",
            json={"password_required": True, "email": "user@test.com"},
            status=200,
        )

        result = client.check_verification_token("tok_verify_123")

        assert isinstance(result, VerificationTokenStatus)
        assert result.password_required is True
        assert result.email == "user@test.com"


class TestVerifyEmail:
    @responses.activate
    def test_success_with_password(self, client: AegisClient) -> None:
        responses.add(
            responses.POST, f"{API_URL}/api/auth/verify-email",
            json={
                "user": make_user_dict(is_verified=True),
                "redirect_url": "https://test.example.com/welcome",
            },
            status=200,
        )

        result = client.verify_email("tok_verify_123", password="newpass123")

        assert isinstance(result, VerificationResult)
        assert result.user.is_verified is True
        assert result.redirect_url == "https://test.example.com/welcome"

    @responses.activate
    def test_success_without_password(self, client: AegisClient) -> None:
        responses.add(
            responses.POST, f"{API_URL}/api/auth/verify-email",
            json={
                "user": make_user_dict(is_verified=True),
                "redirect_url": "https://test.example.com",
            },
            status=200,
        )

        result = client.verify_email("tok_verify_123")
        body = responses.calls[0].request.body.decode()
        assert "password" not in body
