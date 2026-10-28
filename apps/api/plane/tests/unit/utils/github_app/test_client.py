# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from datetime import timedelta
from unittest.mock import Mock, patch

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from django.core.cache import cache
from django.utils import timezone

from plane.utils.github_app.client import GithubAppAPIError, GithubAppClient, GithubAppConfigError

PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
PRIVATE_KEY_PEM = PRIVATE_KEY.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.TraditionalOpenSSL,
    encryption_algorithm=serialization.NoEncryption(),
).decode()
PUBLIC_KEY_PEM = PRIVATE_KEY.public_key().public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo,
).decode()


@pytest.fixture(autouse=True)
def _configured_app(settings):
    settings.GITHUB_APP_ID = "12345"
    settings.GITHUB_APP_PRIVATE_KEY = PRIVATE_KEY_PEM
    cache.clear()
    yield
    cache.clear()


def _response(status_code, json_data=None, headers=None):
    response = Mock()
    response.status_code = status_code
    response.headers = headers or {}
    response.json.return_value = json_data or {}
    response.links = {}
    response.request = Mock(method="GET", path_url="/some/path")
    return response


@pytest.mark.unit
class TestGithubAppClientJWT:
    def test_builds_a_valid_rs256_jwt_with_expected_claims(self):
        client = GithubAppClient(installation_id=1)
        token = client._build_jwt()

        decoded = jwt.decode(token, PUBLIC_KEY_PEM, algorithms=["RS256"])
        assert decoded["iss"] == "12345"
        assert decoded["exp"] > decoded["iat"]

    def test_raises_config_error_when_app_not_configured(self, settings):
        settings.GITHUB_APP_ID = ""
        settings.GITHUB_APP_PRIVATE_KEY = ""
        client = GithubAppClient(installation_id=1)
        with pytest.raises(GithubAppConfigError):
            client._build_jwt()

    def test_accepts_private_key_with_literal_newline_escapes(self):
        settings_key = PRIVATE_KEY_PEM.replace("\n", "\\n")
        with patch("plane.utils.github_app.client.settings") as mock_settings:
            mock_settings.GITHUB_APP_ID = "12345"
            mock_settings.GITHUB_APP_PRIVATE_KEY = settings_key
            client = GithubAppClient(installation_id=1)
            token = client._build_jwt()
        jwt.decode(token, PUBLIC_KEY_PEM, algorithms=["RS256"])


@pytest.mark.unit
class TestGithubAppClientTokenCaching:
    def test_installation_token_is_cached_across_calls(self):
        client = GithubAppClient(installation_id=42)
        expires_at = (timezone.now() + timedelta(minutes=10)).isoformat()
        token_response = _response(201, {"token": "ghs_secret_token", "expires_at": expires_at})

        with patch("plane.utils.github_app.client.requests.request", return_value=token_response) as mock_request:
            first = client._installation_token()
            second = client._installation_token()

        assert first == second == "ghs_secret_token"
        assert mock_request.call_count == 1

    def test_installation_token_cache_expires_before_github_expiry(self):
        client = GithubAppClient(installation_id=42)
        expires_at = (timezone.now() + timedelta(seconds=65)).isoformat()
        token_response = _response(201, {"token": "ghs_secret_token", "expires_at": expires_at})

        with patch("plane.utils.github_app.client.requests.request", return_value=token_response):
            client._installation_token()

        ttl = cache.ttl("github_app:installation_token:42")
        assert 0 <= ttl <= 6


@pytest.mark.unit
class TestGithubAppClientRetries:
    def test_retries_on_5xx_and_429_then_succeeds(self):
        client = GithubAppClient(installation_id=1)
        responses = [_response(500), _response(429), _response(200, {"ok": True})]

        with patch("plane.utils.github_app.client.requests.request", side_effect=responses) as mock_request, patch(
            "plane.utils.github_app.client.time.sleep"
        ) as mock_sleep:
            result = client._request("GET", "https://api.github.com/x", headers={})

        assert result.status_code == 200
        assert mock_request.call_count == 3
        assert mock_sleep.call_count == 2

    def test_retries_on_secondary_rate_limit_with_retry_after(self):
        client = GithubAppClient(installation_id=1)
        responses = [_response(403, headers={"Retry-After": "1"}), _response(200, {"ok": True})]

        with patch("plane.utils.github_app.client.requests.request", side_effect=responses), patch(
            "plane.utils.github_app.client.time.sleep"
        ) as mock_sleep:
            result = client._request("GET", "https://api.github.com/x", headers={})

        assert result.status_code == 200
        mock_sleep.assert_called_once_with(1.0)

    def test_does_not_retry_plain_403(self):
        client = GithubAppClient(installation_id=1)
        forbidden = _response(403)

        with patch("plane.utils.github_app.client.requests.request", return_value=forbidden) as mock_request:
            result = client._request("GET", "https://api.github.com/x", headers={})

        assert result.status_code == 403
        assert mock_request.call_count == 1

    def test_gives_up_after_max_attempts(self):
        client = GithubAppClient(installation_id=1)
        always_500 = _response(500)

        with patch("plane.utils.github_app.client.requests.request", return_value=always_500) as mock_request, patch(
            "plane.utils.github_app.client.time.sleep"
        ):
            with pytest.raises(GithubAppAPIError) as exc_info:
                result = client._request("GET", "https://api.github.com/x", headers={})
                client._raise_for_status(result)

        assert mock_request.call_count == 5
        assert "500" in str(exc_info.value)


@pytest.mark.unit
class TestGithubAppClientPagination:
    """_auth_headers is stubbed out so these exercise only the pagination/retry
    logic, not the separate installation-token fetch (covered above)."""

    def test_list_repo_issues_follows_pagination_links(self):
        client = GithubAppClient(installation_id=1)
        page1 = _response(200, [{"number": 1}])
        page1.links = {"next": {"url": "https://api.github.com/repos/acme/widgets/issues?page=2"}}
        page2 = _response(200, [{"number": 2}])

        with patch.object(client, "_auth_headers", return_value={}), patch(
            "plane.utils.github_app.client.requests.request", side_effect=[page1, page2]
        ) as mock_request:
            issues = client.list_repo_issues("acme/widgets", state="open")

        assert [issue["number"] for issue in issues] == [1, 2]
        assert mock_request.call_count == 2

    def test_list_repo_issues_retries_on_secondary_rate_limit_then_succeeds(self):
        client = GithubAppClient(installation_id=1)
        rate_limited = _response(403, headers={"Retry-After": "0"})
        ok = _response(200, [{"number": 1}])

        with patch.object(client, "_auth_headers", return_value={}), patch(
            "plane.utils.github_app.client.requests.request", side_effect=[rate_limited, ok]
        ) as mock_request, patch("plane.utils.github_app.client.time.sleep") as mock_sleep:
            issues = client.list_repo_issues("acme/widgets")

        assert issues == [{"number": 1}]
        assert mock_request.call_count == 2
        mock_sleep.assert_called_once_with(0.0)

    def test_list_repo_issues_raises_after_exhausting_retries_on_primary_rate_limit(self):
        client = GithubAppClient(installation_id=1)
        exhausted = _response(403, headers={"X-RateLimit-Remaining": "0"})

        with patch.object(client, "_auth_headers", return_value={}), patch(
            "plane.utils.github_app.client.requests.request", return_value=exhausted
        ) as mock_request, patch("plane.utils.github_app.client.time.sleep"):
            with pytest.raises(GithubAppAPIError):
                client.list_repo_issues("acme/widgets")

        assert mock_request.call_count == 5


@pytest.mark.unit
class TestGithubAppClientRedaction:
    def test_error_message_never_contains_the_token_or_jwt(self):
        client = GithubAppClient(installation_id=1)
        app_jwt = client._build_jwt()
        headers = {"Authorization": f"Bearer {app_jwt}"}
        failing = _response(400)

        with patch("plane.utils.github_app.client.requests.request", return_value=failing):
            result = client._request("GET", "https://api.github.com/x", headers=headers)
            with pytest.raises(GithubAppAPIError) as exc_info:
                client._raise_for_status(result)

        assert app_jwt not in str(exc_info.value)

    def test_connection_error_message_never_contains_the_token(self):
        import requests

        client = GithubAppClient(installation_id=1)
        app_jwt = client._build_jwt()
        headers = {"Authorization": f"Bearer {app_jwt}"}

        with patch(
            "plane.utils.github_app.client.requests.request",
            side_effect=requests.ConnectionError(f"failed with Bearer {app_jwt}"),
        ), patch("plane.utils.github_app.client.time.sleep"):
            with pytest.raises(GithubAppAPIError) as exc_info:
                client._request("GET", "https://api.github.com/x", headers=headers)

        assert app_jwt not in str(exc_info.value)
