"""Tests for AegisClient.me() — token introspection."""
import pytest
import responses

from byteforge_aegis_client import (
    AegisApiError,
    AegisClient,
    AegisUnauthorized,
)
from byteforge_aegis_models import User

from conftest import API_URL, make_user_dict


class TestMe:
    @responses.activate
    def test_success(self, authed_client: AegisClient) -> None:
        responses.add(
            responses.GET, f"{API_URL}/api/auth/me",
            json=make_user_dict(), status=200,
        )

        user = authed_client.me()

        assert isinstance(user, User)
        assert user.id == 10
        assert user.email == "user@test.com"
        auth_header = responses.calls[0].request.headers["Authorization"]
        assert auth_header == "Bearer test_auth_token"

    def test_no_auth_token(self, client: AegisClient) -> None:
        with pytest.raises(ValueError, match="Authentication token"):
            client.me()

    @responses.activate
    def test_unauthorized_raises_typed_exception(
        self, authed_client: AegisClient
    ) -> None:
        responses.add(
            responses.GET, f"{API_URL}/api/auth/me",
            json={"error": "Invalid or expired token"}, status=401,
        )

        with pytest.raises(AegisUnauthorized) as exc_info:
            authed_client.me()

        assert exc_info.value.status_code == 401
        assert "Invalid or expired token" in exc_info.value.message

    @responses.activate
    def test_unauthorized_is_also_api_error(
        self, authed_client: AegisClient
    ) -> None:
        """AegisUnauthorized subclasses AegisApiError — existing catches still work."""
        responses.add(
            responses.GET, f"{API_URL}/api/auth/me",
            json={"error": "Invalid or expired token"}, status=401,
        )

        with pytest.raises(AegisApiError):
            authed_client.me()
