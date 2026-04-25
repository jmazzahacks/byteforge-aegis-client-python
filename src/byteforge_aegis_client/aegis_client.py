"""Main Aegis API client."""
import time
from typing import Any, Dict, List, Optional
from urllib.parse import quote

from byteforge_aegis_models import (
    EmailChangeResponse,
    HealthStatus,
    LoginResult,
    MessageResponse,
    Site,
    User,
    VerificationResult,
    VerificationTokenStatus,
)

from byteforge_aegis_client._http import HttpSession
from byteforge_aegis_client.config import AegisClientConfig
from byteforge_aegis_client.request_models import CreateSiteRequest, UpdateSiteRequest


class AegisClient:
    """
    Python client for the ByteForge Aegis multi-tenant authentication API.

    Mirrors the JavaScript AuthClient API surface.
    All methods raise AegisApiError on HTTP errors or AegisNetworkError
    on connection failures.
    """

    def __init__(self, config: AegisClientConfig) -> None:
        self._config = config
        self._auth_token: Optional[str] = None
        self._auth_token_expires_at: Optional[int] = None
        self._refresh_token: Optional[str] = None

        self._http = HttpSession(
            api_url=config.api_url,
            get_auth_token=self.get_auth_token,
            get_master_api_key=self._get_master_api_key,
            get_tenant_api_key=self._get_tenant_api_key,
            should_refresh=self._should_refresh_token,
            do_refresh=self._do_refresh,
            auto_refresh=config.auto_refresh,
        )

    # ========================================================================
    # Token management
    # ========================================================================

    def set_auth_token(self, token: str) -> None:
        """Set the authentication bearer token."""
        self._auth_token = token

    def get_auth_token(self) -> Optional[str]:
        """Get the current authentication token."""
        return self._auth_token

    def clear_auth_token(self) -> None:
        """Clear the authentication token and expiration."""
        self._auth_token = None
        self._auth_token_expires_at = None

    def set_refresh_token(self, token: str) -> None:
        """Set the refresh token."""
        self._refresh_token = token

    def get_refresh_token(self) -> Optional[str]:
        """Get the current refresh token."""
        return self._refresh_token

    def clear_refresh_token(self) -> None:
        """Clear the refresh token."""
        self._refresh_token = None

    def clear_all_tokens(self) -> None:
        """Clear both auth and refresh tokens."""
        self.clear_auth_token()
        self.clear_refresh_token()

    def _get_master_api_key(self) -> Optional[str]:
        """Get the master API key from config."""
        return self._config.master_api_key

    def _get_tenant_api_key(self) -> Optional[str]:
        """Get the tenant API key from config."""
        return self._config.tenant_api_key

    def _should_refresh_token(self) -> bool:
        """Check if the auth token should be proactively refreshed."""
        if not self._auth_token_expires_at or not self._refresh_token:
            return False
        return int(time.time()) + self._config.refresh_buffer_seconds >= self._auth_token_expires_at

    def _set_tokens_from_login(self, result: LoginResult) -> None:
        """Set tokens from a parsed login/refresh result."""
        self._auth_token = result.auth_token.token
        self._auth_token_expires_at = result.auth_token.expires_at
        if result.refresh_token:
            self._refresh_token = result.refresh_token.token

    def _do_refresh(self) -> bool:
        """Attempt to refresh the auth token. Returns True if successful."""
        if not self._refresh_token:
            return False
        try:
            self.refresh_auth_token()
            return True
        except Exception:
            return False

    def _require_site_id(self, site_id: Optional[int] = None) -> int:
        """Get site_id from argument or config, raising if neither available."""
        resolved = site_id or self._config.site_id
        if not resolved:
            raise ValueError("site_id is required but not provided and not set in config")
        return resolved

    def _require_auth_token(self) -> str:
        """Get auth token, raising if not available."""
        if not self._auth_token:
            raise ValueError("Authentication token is required but not set")
        return self._auth_token

    def _require_master_api_key(self) -> str:
        """Get master API key, raising if not available."""
        if not self._config.master_api_key:
            raise ValueError("Master API key is required but not set in config")
        return self._config.master_api_key

    # ========================================================================
    # Health
    # ========================================================================

    def health_check(self) -> HealthStatus:
        """Check API health. GET /api/health"""
        data = self._http.request('GET', '/api/health')
        return HealthStatus.from_dict(data)

    # ========================================================================
    # Token refresh
    # ========================================================================

    def refresh_auth_token(self) -> LoginResult:
        """Refresh the auth token. POST /api/auth/refresh"""
        if not self._refresh_token:
            raise ValueError("No refresh token available")

        data = self._http.request(
            'POST', '/api/auth/refresh',
            json_body={'refresh_token': self._refresh_token},
            skip_auto_refresh=True,
        )
        result = LoginResult.from_dict(data)
        self._set_tokens_from_login(result)
        return result

    # ========================================================================
    # Public site operations
    # ========================================================================

    def get_site_by_domain(self, domain: str) -> Site:
        """Get a site by domain. GET /api/sites/by-domain?domain=..."""
        encoded = quote(domain, safe='')
        data = self._http.request('GET', f'/api/sites/by-domain?domain={encoded}')
        return Site.from_dict(data)

    # ========================================================================
    # User authentication
    # ========================================================================

    def register(
        self, email: str, password: Optional[str] = None, site_id: Optional[int] = None
    ) -> User:
        """Register a new user. POST /api/auth/register"""
        resolved_site_id = self._require_site_id(site_id)
        body: Dict[str, Any] = {'site_id': resolved_site_id, 'email': email}
        if password:
            body['password'] = password
        data = self._http.request('POST', '/api/auth/register', body)
        return User.from_dict(data)

    def login(
        self, email: str, password: str, site_id: Optional[int] = None
    ) -> LoginResult:
        """Login a user. POST /api/auth/login. Auto-sets tokens on success."""
        resolved_site_id = self._require_site_id(site_id)
        body = {'site_id': resolved_site_id, 'email': email, 'password': password}
        data = self._http.request('POST', '/api/auth/login', body, skip_auto_refresh=True)
        result = LoginResult.from_dict(data)
        self._set_tokens_from_login(result)
        return result

    def logout(self) -> MessageResponse:
        """Logout the current user. POST /api/auth/logout. Clears all tokens."""
        token = self._require_auth_token()
        try:
            data = self._http.request('POST', '/api/auth/logout', {'token': token})
        finally:
            self.clear_all_tokens()
        return MessageResponse.from_dict(data)

    def check_verification_token(self, token: str) -> VerificationTokenStatus:
        """Check a verification token. POST /api/auth/check-verification-token

        site_id is auto-included from config when set; otherwise the caller
        (typically a tenant proxy route) is expected to add it.
        """
        body: Dict[str, Any] = {'token': token}
        if self._config.site_id:
            body['site_id'] = self._config.site_id
        data = self._http.request(
            'POST', '/api/auth/check-verification-token', body
        )
        return VerificationTokenStatus.from_dict(data)

    def verify_email(
        self, token: str, password: Optional[str] = None
    ) -> VerificationResult:
        """Verify an email address. POST /api/auth/verify-email

        site_id is auto-included from config when set; otherwise the caller
        (typically a tenant proxy route) is expected to add it.
        """
        body: Dict[str, Any] = {'token': token}
        if self._config.site_id:
            body['site_id'] = self._config.site_id
        if password:
            body['password'] = password
        data = self._http.request('POST', '/api/auth/verify-email', body)
        return VerificationResult.from_dict(data)

    def me(self) -> User:
        """
        Return the user associated with the current bearer token.
        GET /api/auth/me

        Raises:
            ValueError: if no auth token is set on the client.
            AegisUnauthorized: if the token is missing, malformed, unknown, or expired.
        """
        self._require_auth_token()
        data = self._http.request('GET', '/api/auth/me')
        return User.from_dict(data)

    def change_password(self, old_password: str, new_password: str) -> User:
        """Change the current user's password. POST /api/auth/change-password"""
        self._require_auth_token()
        body = {'old_password': old_password, 'new_password': new_password}
        data = self._http.request('POST', '/api/auth/change-password', body)
        return User.from_dict(data)

    def request_password_reset(
        self, email: str, site_id: Optional[int] = None
    ) -> MessageResponse:
        """Request a password reset email. POST /api/auth/request-password-reset"""
        resolved_site_id = self._require_site_id(site_id)
        body = {'site_id': resolved_site_id, 'email': email}
        data = self._http.request('POST', '/api/auth/request-password-reset', body)
        return MessageResponse.from_dict(data)

    def reset_password(self, token: str, new_password: str) -> User:
        """Reset password with a token. POST /api/auth/reset-password

        site_id is auto-included from config when set; otherwise the caller
        (typically a tenant proxy route) is expected to add it.
        """
        body: Dict[str, Any] = {'token': token, 'new_password': new_password}
        if self._config.site_id:
            body['site_id'] = self._config.site_id
        data = self._http.request('POST', '/api/auth/reset-password', body)
        return User.from_dict(data)

    def request_email_change(self, new_email: str) -> EmailChangeResponse:
        """Request an email change. POST /api/auth/request-email-change"""
        self._require_auth_token()
        data = self._http.request(
            'POST', '/api/auth/request-email-change', {'new_email': new_email}
        )
        return EmailChangeResponse.from_dict(data)

    def confirm_email_change(self, token: str) -> User:
        """Confirm an email change. POST /api/auth/confirm-email-change"""
        data = self._http.request(
            'POST', '/api/auth/confirm-email-change', {'token': token}
        )
        return User.from_dict(data)

    # ========================================================================
    # Admin operations (Bearer token auth)
    # ========================================================================

    def admin_list_users(self) -> List[User]:
        """List users for the admin's site. GET /api/admin/users"""
        self._require_auth_token()
        data = self._http.request('GET', '/api/admin/users')
        return [User.from_dict(u) for u in data]

    # ========================================================================
    # Admin operations (Master API key auth)
    # ========================================================================

    def register_admin(
        self, email: str, site_id: int, role: Optional[str] = None
    ) -> User:
        """Register an admin user. POST /api/admin/register"""
        self._require_master_api_key()
        body: Dict[str, Any] = {'site_id': site_id, 'email': email}
        if role:
            body['role'] = role
        data = self._http.request('POST', '/api/admin/register', body)
        return User.from_dict(data)

    def create_site(self, site_data: CreateSiteRequest) -> Site:
        """Create a new site. POST /api/sites"""
        self._require_master_api_key()
        data = self._http.request('POST', '/api/sites', site_data.to_dict())
        return Site.from_dict(data)

    def get_site(self, site_id: int) -> Site:
        """Get a site by ID. GET /api/sites/{site_id}"""
        self._require_master_api_key()
        data = self._http.request('GET', f'/api/sites/{site_id}')
        return Site.from_dict(data)

    def list_sites(self) -> List[Site]:
        """List all sites. GET /api/sites"""
        self._require_master_api_key()
        data = self._http.request('GET', '/api/sites')
        return [Site.from_dict(s) for s in data]

    def list_users_by_site(self, site_id: int) -> List[User]:
        """List users for a site. GET /api/sites/{site_id}/users"""
        self._require_master_api_key()
        data = self._http.request('GET', f'/api/sites/{site_id}/users')
        return [User.from_dict(u) for u in data]

    def update_site(self, site_id: int, updates: UpdateSiteRequest) -> Site:
        """Update a site. PUT /api/sites/{site_id}"""
        self._require_master_api_key()
        data = self._http.request('PUT', f'/api/sites/{site_id}', updates.to_dict())
        return Site.from_dict(data)

    # ========================================================================
    # Aegis Admin operations (used by admin frontend)
    # ========================================================================

    def aegis_admin_list_sites(self, admin_token: str) -> List[Site]:
        """List all sites using an admin bearer token. GET /api/sites"""
        old_token = self._auth_token
        self._auth_token = admin_token
        try:
            data = self._http.request('GET', '/api/sites', skip_auto_refresh=True)
        finally:
            self._auth_token = old_token
        return [Site.from_dict(s) for s in data]

    def aegis_admin_list_users_by_site(
        self, site_id: int, admin_token: str
    ) -> List[User]:
        """List users for a site using an admin bearer token."""
        old_token = self._auth_token
        self._auth_token = admin_token
        try:
            data = self._http.request(
                'GET', f'/api/sites/{site_id}/users', skip_auto_refresh=True
            )
        finally:
            self._auth_token = old_token
        return [User.from_dict(u) for u in data]
