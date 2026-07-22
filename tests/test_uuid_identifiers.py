"""Tests for UUID identifier handling (post-contract: UUID is the only form).

The client passes site/user UUIDs through to the API unchanged (in config or
per-call) and surfaces the uuid/site_uuid fields the API returns.
"""
import responses

from byteforge_aegis_client import AegisClient, AegisClientConfig
from byteforge_aegis_models import User

from conftest import (
    API_URL,
    SITE_UUID,
    USER_UUID,
    make_login_response_dict,
    make_site_dict,
    make_user_dict,
)


class TestUuidRequestPassthrough:
    @responses.activate
    def test_login_with_uuid_site_id_arg(self) -> None:
        client = AegisClient(AegisClientConfig(api_url=API_URL, auto_refresh=False))
        responses.add(responses.POST, f"{API_URL}/api/auth/login",
                      json=make_login_response_dict(), status=200)

        client.login("user@test.com", "pw", site_id=SITE_UUID)

        body = responses.calls[0].request.body.decode()
        assert f'"site_id": "{SITE_UUID}"' in body

    @responses.activate
    def test_login_with_uuid_site_id_from_config(self) -> None:
        client = AegisClient(AegisClientConfig(
            api_url=API_URL, site_id=SITE_UUID, auto_refresh=False,
        ))
        responses.add(responses.POST, f"{API_URL}/api/auth/login",
                      json=make_login_response_dict(), status=200)

        client.login("user@test.com", "pw")

        body = responses.calls[0].request.body.decode()
        assert f'"site_id": "{SITE_UUID}"' in body

    @responses.activate
    def test_get_site_by_uuid_builds_uuid_url(self, admin_client: AegisClient) -> None:
        responses.add(responses.GET, f"{API_URL}/api/sites/{SITE_UUID}",
                      json=make_site_dict(), status=200)

        site = admin_client.get_site(SITE_UUID)

        assert responses.calls[0].request.url.endswith(f"/api/sites/{SITE_UUID}")
        assert site.uuid == SITE_UUID

    @responses.activate
    def test_get_user_by_uuid_builds_uuid_url(self, tenant_client: AegisClient) -> None:
        responses.add(
            responses.GET,
            f"{API_URL}/api/sites/{SITE_UUID}/users/{USER_UUID}",
            json=make_user_dict(), status=200,
        )

        user = tenant_client.get_user(USER_UUID, site_id=SITE_UUID)

        assert responses.calls[0].request.url.endswith(
            f"/api/sites/{SITE_UUID}/users/{USER_UUID}"
        )
        assert user.uuid == USER_UUID
        assert user.site_uuid == SITE_UUID


class TestUuidResponseParsing:
    @responses.activate
    def test_me_exposes_uuid_fields(self, authed_client: AegisClient) -> None:
        responses.add(responses.GET, f"{API_URL}/api/auth/me",
                      json=make_user_dict(), status=200)

        user = authed_client.me()

        assert isinstance(user, User)
        assert user.uuid == USER_UUID
        assert user.site_uuid == SITE_UUID

    @responses.activate
    def test_login_result_tokens_carry_uuids(self) -> None:
        client = AegisClient(AegisClientConfig(
            api_url=API_URL, site_id=SITE_UUID, auto_refresh=False,
        ))
        responses.add(responses.POST, f"{API_URL}/api/auth/login",
                      json=make_login_response_dict(), status=200)

        result = client.login("user@test.com", "pw")

        assert result.auth_token.user_uuid == USER_UUID
        assert result.refresh_token is not None
        assert result.refresh_token.site_uuid == SITE_UUID
        assert result.refresh_token.user_uuid == USER_UUID
