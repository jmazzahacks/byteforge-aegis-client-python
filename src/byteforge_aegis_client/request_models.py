from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class CreateSiteRequest:
    """
    Request to create a new site.

    Attributes:
        name: Human-readable site name
        domain: Domain name (unique)
        frontend_url: Frontend URL for email links
        email_from: Email address to send from
        email_from_name: Display name for outgoing emails
        verification_redirect_url: URL to redirect to after email verification
        allow_self_registration: Whether public self-registration is enabled
        webhook_url: URL to receive webhook notifications
    """
    name: str
    domain: str
    frontend_url: str
    email_from: str
    email_from_name: str
    verification_redirect_url: Optional[str] = None
    allow_self_registration: Optional[bool] = None
    webhook_url: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        result: Dict[str, Any] = {
            'name': self.name,
            'domain': self.domain,
            'frontend_url': self.frontend_url,
            'email_from': self.email_from,
            'email_from_name': self.email_from_name,
        }
        if self.verification_redirect_url is not None:
            result['verification_redirect_url'] = self.verification_redirect_url
        if self.allow_self_registration is not None:
            result['allow_self_registration'] = self.allow_self_registration
        if self.webhook_url is not None:
            result['webhook_url'] = self.webhook_url
        return result


@dataclass
class UpdateSiteRequest:
    """
    Request to update an existing site. Only non-None fields are sent.

    Attributes:
        name: New site name
        domain: New domain
        frontend_url: New frontend URL
        verification_redirect_url: New verification redirect URL
        email_from: New email from address
        email_from_name: New email from name
        allow_self_registration: Enable/disable self-registration
        webhook_url: New webhook URL (set to empty string to clear)
        regenerate_webhook_secret: Whether to regenerate the webhook secret
        regenerate_tenant_api_key: Whether to regenerate the tenant API key
    """
    name: Optional[str] = None
    domain: Optional[str] = None
    frontend_url: Optional[str] = None
    verification_redirect_url: Optional[str] = None
    email_from: Optional[str] = None
    email_from_name: Optional[str] = None
    allow_self_registration: Optional[bool] = None
    webhook_url: Optional[str] = field(default=None)
    regenerate_webhook_secret: Optional[bool] = None
    regenerate_tenant_api_key: Optional[bool] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, only including explicitly set fields."""
        result: Dict[str, Any] = {}
        if self.name is not None:
            result['name'] = self.name
        if self.domain is not None:
            result['domain'] = self.domain
        if self.frontend_url is not None:
            result['frontend_url'] = self.frontend_url
        if self.verification_redirect_url is not None:
            result['verification_redirect_url'] = self.verification_redirect_url
        if self.email_from is not None:
            result['email_from'] = self.email_from
        if self.email_from_name is not None:
            result['email_from_name'] = self.email_from_name
        if self.allow_self_registration is not None:
            result['allow_self_registration'] = self.allow_self_registration
        if self.webhook_url is not None:
            result['webhook_url'] = self.webhook_url
        if self.regenerate_webhook_secret is not None:
            result['regenerate_webhook_secret'] = self.regenerate_webhook_secret
        if self.regenerate_tenant_api_key is not None:
            result['regenerate_tenant_api_key'] = self.regenerate_tenant_api_key
        return result
