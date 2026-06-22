"""Tests for UUID identifier support (int -> UUID migration, dual phase).

The client must accept a site/user identifier as either an integer id or a
UUID string (in config or per-call) and pass it through to the API unchanged,
and must surface the uuid/site_uuid fields the API now returns.
"""
import responses

from byteforge_aegis_client import AegisClient, AegisClientConfig
from byteforge_aegis_models import Site, User

from conftest import API_URL, make_login_response_dict, make_site_dict, make_user_dict

SITE_UUID = "0191e1a0-0000-7000-8000-000000000001"
USER_UUID = "0191e1a0-0000-7000-8000-0000000000aa"


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
        site_dict = make_site_dict()
        site_dict["uuid"] = SITE_UUID
        responses.add(responses.GET, f"{API_URL}/api/sites/{SITE_UUID}",
                      json=site_dict, status=200)

        site = admin_client.get_site(SITE_UUID)

        assert responses.calls[0].request.url.endswith(f"/api/sites/{SITE_UUID}")
        assert site.uuid == SITE_UUID

    @responses.activate
    def test_get_user_by_uuid_builds_uuid_url(self, tenant_client: AegisClient) -> None:
        user_dict = make_user_dict()
        user_dict["uuid"] = USER_UUID
        user_dict["site_uuid"] = SITE_UUID
        responses.add(
            responses.GET,
            f"{API_URL}/api/sites/{SITE_UUID}/users/{USER_UUID}",
            json=user_dict, status=200,
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
        user_dict = make_user_dict()
        user_dict["uuid"] = USER_UUID
        user_dict["site_uuid"] = SITE_UUID
        responses.add(responses.GET, f"{API_URL}/api/auth/me", json=user_dict, status=200)

        user = authed_client.me()

        assert isinstance(user, User)
        assert user.uuid == USER_UUID
        assert user.site_uuid == SITE_UUID

    @responses.activate
    def test_int_site_id_still_passed_through(self, client: AegisClient) -> None:
        """Integer addressing must keep working unchanged."""
        responses.add(responses.POST, f"{API_URL}/api/auth/login",
                      json=make_login_response_dict(), status=200)

        client.login("user@test.com", "pw", site_id=5)

        body = responses.calls[0].request.body.decode()
        assert '"site_id": 5' in body
