"""Tests for site management methods."""
import pytest
import responses

from byteforge_aegis_client import AegisClient, AegisApiError, CreateSiteRequest, UpdateSiteRequest
from byteforge_aegis_models import Site

from conftest import API_URL, make_site_dict


class TestGetSiteByDomain:
    @responses.activate
    def test_success(self, client: AegisClient) -> None:
        responses.add(
            responses.GET,
            f"{API_URL}/api/sites/by-domain?domain=test.example.com",
            json=make_site_dict(), status=200,
        )

        result = client.get_site_by_domain("test.example.com")

        assert isinstance(result, Site)
        assert result.domain == "test.example.com"

    @responses.activate
    def test_not_found(self, client: AegisClient) -> None:
        responses.add(
            responses.GET,
            f"{API_URL}/api/sites/by-domain?domain=unknown.com",
            json={"error": "Site not found"}, status=404,
        )

        with pytest.raises(AegisApiError) as exc_info:
            client.get_site_by_domain("unknown.com")
        assert exc_info.value.status_code == 404


class TestAdminSiteOperations:
    @responses.activate
    def test_list_sites(self, admin_client: AegisClient) -> None:
        responses.add(
            responses.GET, f"{API_URL}/api/sites",
            json=[make_site_dict(1), make_site_dict(2)], status=200,
        )

        sites = admin_client.list_sites()

        assert len(sites) == 2
        assert all(isinstance(s, Site) for s in sites)
        assert responses.calls[0].request.headers["X-API-Key"] == "master_key_123"

    @responses.activate
    def test_get_site(self, admin_client: AegisClient) -> None:
        responses.add(
            responses.GET, f"{API_URL}/api/sites/1",
            json=make_site_dict(), status=200,
        )

        site = admin_client.get_site(1)
        assert site.id == 1

    @responses.activate
    def test_create_site(self, admin_client: AegisClient) -> None:
        responses.add(
            responses.POST, f"{API_URL}/api/sites",
            json=make_site_dict(), status=201,
        )

        site = admin_client.create_site(CreateSiteRequest(
            name="Test Site",
            domain="test.example.com",
            frontend_url="https://test.example.com",
            email_from="noreply@test.example.com",
            email_from_name="Test Site",
        ))
        assert isinstance(site, Site)

    @responses.activate
    def test_update_site(self, admin_client: AegisClient) -> None:
        updated = make_site_dict()
        updated["name"] = "Updated Site"
        responses.add(
            responses.PUT, f"{API_URL}/api/sites/1",
            json=updated, status=200,
        )

        site = admin_client.update_site(1, UpdateSiteRequest(name="Updated Site"))
        assert site.name == "Updated Site"

    def test_list_sites_no_api_key(self, client: AegisClient) -> None:
        with pytest.raises(ValueError, match="Master API key"):
            client.list_sites()

    @responses.activate
    def test_list_users_by_site(self, admin_client: AegisClient) -> None:
        from conftest import make_user_dict
        responses.add(
            responses.GET, f"{API_URL}/api/sites/1/users",
            json=[make_user_dict(), make_user_dict(user_id=11, email="other@test.com")],
            status=200,
        )

        users = admin_client.list_users_by_site(1)
        assert len(users) == 2
