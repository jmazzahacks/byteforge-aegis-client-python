"""Internal HTTP session handling for the Aegis client."""
from typing import Any, Callable, Dict, Optional

import requests

from byteforge_aegis_client.exceptions import AegisApiError, AegisNetworkError


class HttpSession:
    """
    Internal HTTP session that handles header injection, proactive token
    refresh, and reactive 401 retry.
    """

    def __init__(
        self,
        api_url: str,
        get_auth_token: Callable[[], Optional[str]],
        get_master_api_key: Callable[[], Optional[str]],
        should_refresh: Callable[[], bool],
        do_refresh: Callable[[], bool],
        auto_refresh: bool,
    ) -> None:
        self._api_url = api_url.rstrip('/')
        self._get_auth_token = get_auth_token
        self._get_master_api_key = get_master_api_key
        self._should_refresh = should_refresh
        self._do_refresh = do_refresh
        self._auto_refresh = auto_refresh
        self._session = requests.Session()

    def request(
        self,
        method: str,
        endpoint: str,
        json_body: Optional[Dict[str, Any]] = None,
        skip_auto_refresh: bool = False,
    ) -> Dict[str, Any]:
        """
        Make an HTTP request to the API.

        Returns:
            Parsed JSON response as a dictionary.

        Raises:
            AegisApiError: If the API returns a non-2xx response.
            AegisNetworkError: If a network/connection error occurs.
        """
        if self._auto_refresh and not skip_auto_refresh and self._should_refresh():
            self._do_refresh()

        url = f"{self._api_url}{endpoint}"
        headers = self._build_headers()

        response = self._send(method, url, json_body, headers)

        if response.status_code == 401 and not skip_auto_refresh:
            refreshed = self._do_refresh()
            if refreshed:
                headers = self._build_headers()
                response = self._send(method, url, json_body, headers)

        return self._parse_response(response)

    def _send(
        self,
        method: str,
        url: str,
        json_body: Optional[Dict[str, Any]],
        headers: Dict[str, str],
    ) -> requests.Response:
        """Send an HTTP request, converting connection errors to AegisNetworkError."""
        try:
            return self._session.request(
                method=method,
                url=url,
                json=json_body,
                headers=headers,
                timeout=30,
            )
        except requests.exceptions.RequestException as e:
            raise AegisNetworkError(str(e))

    def _build_headers(self) -> Dict[str, str]:
        """Build request headers with auth token and/or API key."""
        headers: Dict[str, str] = {
            'Content-Type': 'application/json',
        }
        token = self._get_auth_token()
        if token:
            headers['Authorization'] = f"Bearer {token}"
        api_key = self._get_master_api_key()
        if api_key:
            headers['X-API-Key'] = api_key
        return headers

    def _parse_response(self, response: requests.Response) -> Dict[str, Any]:
        """
        Parse an HTTP response, raising AegisApiError on non-2xx status.

        Returns:
            Parsed JSON dict on success.
        """
        try:
            data = response.json()
        except (ValueError, requests.exceptions.JSONDecodeError):
            if 200 <= response.status_code < 300:
                return {}
            raise AegisApiError(response.status_code, response.text or "Unknown error")

        if 200 <= response.status_code < 300:
            return data

        error_msg = data.get('error', 'Unknown error') if isinstance(data, dict) else str(data)
        raise AegisApiError(response.status_code, error_msg)
