"""Tests for site management methods."""
import pytest
import responses

from byteforge_aegis_client import AegisClient, AegisApiError, CreateSiteRequest, UpdateSiteRequest
from byteforge_aegis_models import Site

from conftest import API_URL, SITE_UUID, make_site_dict

OTHER_SITE_UUID = "0191e1a0-0000-7000-8000-000000000002"
UNKNOWN_SITE_UUID = "0191e1a0-0000-7000-8000-0000000fffff"


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
            json=[make_site_dict(SITE_UUID), make_site_dict(OTHER_SITE_UUID)], status=200,
        )

        sites = admin_client.list_sites()

        assert len(sites) == 2
        assert all(isinstance(s, Site) for s in sites)
        assert responses.calls[0].request.headers["X-API-Key"] == "master_key_123"

    @responses.activate
    def test_get_site(self, admin_client: AegisClient) -> None:
        responses.add(
            responses.GET, f"{API_URL}/api/sites/{SITE_UUID}",
            json=make_site_dict(), status=200,
        )

        site = admin_client.get_site(SITE_UUID)
        assert site.uuid == SITE_UUID

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
            responses.PUT, f"{API_URL}/api/sites/{SITE_UUID}",
            json=updated, status=200,
        )

        site = admin_client.update_site(SITE_UUID, UpdateSiteRequest(name="Updated Site"))
        assert site.name == "Updated Site"

    @responses.activate
    def test_update_site_sets_deletion_protection(self, admin_client: AegisClient) -> None:
        """Tenant-wide protection is set through the normal update endpoint."""
        responses.add(
            responses.PUT, f"{API_URL}/api/sites/{SITE_UUID}",
            json=make_site_dict(deletion_protected=True), status=200,
        )

        site = admin_client.update_site(SITE_UUID, UpdateSiteRequest(deletion_protected=True))

        assert site.deletion_protected is True
        assert b'"deletion_protected": true' in responses.calls[0].request.body

    def test_update_request_omits_unset_deletion_protection(self) -> None:
        """An update that doesn't mention protection must not clear it."""
        assert 'deletion_protected' not in UpdateSiteRequest(name="x").to_dict()

    @responses.activate
    def test_delete_site(self, admin_client: AegisClient) -> None:
        responses.add(
            responses.DELETE, f"{API_URL}/api/sites/{SITE_UUID}",
            json={"message": "Site deleted successfully"}, status=200,
        )

        result = admin_client.delete_site(SITE_UUID)

        assert result is None
        assert responses.calls[0].request.headers["X-API-Key"] == "master_key_123"

    @responses.activate
    def test_delete_site_not_found(self, admin_client: AegisClient) -> None:
        responses.add(
            responses.DELETE, f"{API_URL}/api/sites/{UNKNOWN_SITE_UUID}",
            json={"error": "Site not found"}, status=404,
        )

        with pytest.raises(AegisApiError) as exc_info:
            admin_client.delete_site(UNKNOWN_SITE_UUID)
        assert exc_info.value.status_code == 404

    def test_delete_site_no_api_key(self, client: AegisClient) -> None:
        with pytest.raises(ValueError, match="Master API key"):
            client.delete_site(SITE_UUID)

    def test_list_sites_no_api_key(self, client: AegisClient) -> None:
        with pytest.raises(ValueError, match="Master API key"):
            client.list_sites()

    @responses.activate
    def test_list_users_by_site(self, admin_client: AegisClient) -> None:
        from conftest import make_user_dict
        responses.add(
            responses.GET, f"{API_URL}/api/sites/{SITE_UUID}/users",
            json=[
                make_user_dict(),
                make_user_dict(
                    user_uuid="0191e1a0-0000-7000-8000-0000000000bb",
                    email="other@test.com",
                ),
            ],
            status=200,
        )

        users = admin_client.list_users_by_site(SITE_UUID)
        assert len(users) == 2
