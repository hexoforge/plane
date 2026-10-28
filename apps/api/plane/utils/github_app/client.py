# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Python imports
import random
import time

# Third party imports
import jwt
import requests

# Django imports
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from django.utils.dateparse import parse_datetime

GITHUB_API_BASE_URL = "https://api.github.com"
REQUEST_TIMEOUT_SECONDS = 10
MAX_ATTEMPTS = 5
MAX_BACKOFF_SECONDS = 60
JWT_TTL_SECONDS = 540
JWT_CLOCK_DRIFT_SECONDS = 60
TOKEN_CACHE_KEY_PREFIX = "github_app:installation_token:"
TOKEN_EXPIRY_SAFETY_MARGIN_SECONDS = 60


class GithubAppConfigError(Exception):
    """Raised when the GitHub App env vars are missing."""


class GithubAppAPIError(Exception):
    """Raised on a non-2xx GitHub API response. Never include tokens/keys in the message."""


class GithubAppClient:
    """GitHub App API client for a single installation.

    Caches the installation access token in Redis (expired 60s before GitHub's own
    expiry) and retries 5xx/429/secondary-rate-limit responses with backoff. The App
    private key, JWT and installation token are never logged; GithubAppAPIError
    messages only ever contain status codes and URLs, never header/body content.
    """

    def __init__(self, installation_id):
        self.installation_id = installation_id

    # -- auth -----------------------------------------------------------------

    def _build_jwt(self):
        app_id = settings.GITHUB_APP_ID
        private_key = settings.GITHUB_APP_PRIVATE_KEY
        if not app_id or not private_key:
            raise GithubAppConfigError("GitHub App is not configured")

        private_key = private_key.replace("\\n", "\n")
        now = int(time.time())
        payload = {
            "iat": now - JWT_CLOCK_DRIFT_SECONDS,
            "exp": now + JWT_TTL_SECONDS,
            "iss": str(app_id),
        }
        return jwt.encode(payload, private_key, algorithm="RS256")

    def _installation_token(self):
        cache_key = f"{TOKEN_CACHE_KEY_PREFIX}{self.installation_id}"
        token = cache.get(cache_key)
        if token:
            return token

        url = f"{GITHUB_API_BASE_URL}/app/installations/{self.installation_id}/access_tokens"
        response = self._request("POST", url, headers=self._jwt_headers())
        self._raise_for_status(response)
        data = response.json()

        expires_at = parse_datetime(data["expires_at"])
        ttl = max(int((expires_at - timezone.now()).total_seconds()) - TOKEN_EXPIRY_SAFETY_MARGIN_SECONDS, 0)
        token = data["token"]
        cache.set(cache_key, token, ttl)
        return token

    def _jwt_headers(self):
        return {
            "Authorization": f"Bearer {self._build_jwt()}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def _auth_headers(self):
        return {
            "Authorization": f"Bearer {self._installation_token()}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    # -- http with retries ------------------------------------------------------

    def _request(self, method, url, headers, **kwargs):
        attempt = 0
        while True:
            attempt += 1
            try:
                response = requests.request(
                    method, url, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS, **kwargs
                )
            except requests.RequestException as exc:
                if attempt >= MAX_ATTEMPTS:
                    raise GithubAppAPIError(
                        f"GitHub request to {method} {url} failed after {attempt} attempts"
                    ) from exc
                self._sleep_backoff(attempt)
                continue

            if attempt >= MAX_ATTEMPTS or not self._should_retry(response):
                return response
            self._sleep_backoff(attempt, response)

    @staticmethod
    def _should_retry(response):
        if response.status_code in (429, 500, 502, 503, 504):
            return True
        if response.status_code == 403:
            # Secondary rate limit or exhausted primary rate limit.
            if response.headers.get("Retry-After"):
                return True
            if response.headers.get("X-RateLimit-Remaining") == "0":
                return True
        return False

    @staticmethod
    def _sleep_backoff(attempt, response=None):
        delay = None
        if response is not None:
            retry_after = response.headers.get("Retry-After")
            if retry_after is not None:
                try:
                    delay = float(retry_after)
                except ValueError:
                    delay = None
            if delay is None:
                reset_at = response.headers.get("X-RateLimit-Reset")
                if reset_at is not None:
                    try:
                        delay = max(float(reset_at) - time.time(), 0)
                    except ValueError:
                        delay = None
        if delay is None:
            delay = (2 ** (attempt - 1)) + random.uniform(0, 1)
        time.sleep(min(delay, MAX_BACKOFF_SECONDS))

    @staticmethod
    def _raise_for_status(response):
        if response.status_code >= 400:
            raise GithubAppAPIError(
                f"GitHub API error {response.status_code} for {response.request.method} "
                f"{response.request.path_url}"
            )

    # -- API --------------------------------------------------------------------

    def get_installation(self):
        url = f"{GITHUB_API_BASE_URL}/app/installations/{self.installation_id}"
        response = self._request("GET", url, headers=self._jwt_headers())
        self._raise_for_status(response)
        return response.json()

    def list_installation_repos(self):
        repos = []
        url = f"{GITHUB_API_BASE_URL}/installation/repositories"
        params = {"per_page": 100}
        while url:
            response = self._request("GET", url, headers=self._auth_headers(), params=params)
            self._raise_for_status(response)
            data = response.json()
            repos.extend(data.get("repositories", []))
            url = response.links.get("next", {}).get("url")
            params = None
        return repos

    def _paginate(self, url, params=None):
        items = []
        params = dict(params or {})
        params.setdefault("per_page", 100)
        while url:
            response = self._request("GET", url, headers=self._auth_headers(), params=params)
            self._raise_for_status(response)
            items.extend(response.json())
            url = response.links.get("next", {}).get("url")
            params = None
        return items

    def list_repo_issues(self, repo_full_name, state="open"):
        """Includes pull requests - GitHub's issues endpoint returns both; callers
        filter out entries with a "pull_request" key."""
        url = f"{GITHUB_API_BASE_URL}/repos/{repo_full_name}/issues"
        return self._paginate(url, {"state": state})

    def list_repo_pulls(self, repo_full_name, state="all"):
        url = f"{GITHUB_API_BASE_URL}/repos/{repo_full_name}/pulls"
        return self._paginate(url, {"state": state})

    def list_issue_comments(self, repo_full_name, number):
        url = f"{GITHUB_API_BASE_URL}/repos/{repo_full_name}/issues/{number}/comments"
        return self._paginate(url)

    def get_issue(self, repo_full_name, number):
        url = f"{GITHUB_API_BASE_URL}/repos/{repo_full_name}/issues/{number}"
        response = self._request("GET", url, headers=self._auth_headers())
        self._raise_for_status(response)
        return response.json()

    def update_issue_state(self, repo_full_name, number, state, state_reason=None):
        url = f"{GITHUB_API_BASE_URL}/repos/{repo_full_name}/issues/{number}"
        payload = {"state": state}
        if state_reason is not None:
            payload["state_reason"] = state_reason
        response = self._request("PATCH", url, headers=self._auth_headers(), json=payload)
        self._raise_for_status(response)
        return response.json()

    def create_issue_comment(self, repo_full_name, number, body):
        url = f"{GITHUB_API_BASE_URL}/repos/{repo_full_name}/issues/{number}/comments"
        response = self._request("POST", url, headers=self._auth_headers(), json={"body": body})
        self._raise_for_status(response)
        return response.json()

    def update_issue_comment(self, repo_full_name, comment_id, body):
        url = f"{GITHUB_API_BASE_URL}/repos/{repo_full_name}/issues/comments/{comment_id}"
        response = self._request("PATCH", url, headers=self._auth_headers(), json={"body": body})
        self._raise_for_status(response)
        return response.json()

    def delete_issue_comment(self, repo_full_name, comment_id):
        url = f"{GITHUB_API_BASE_URL}/repos/{repo_full_name}/issues/comments/{comment_id}"
        response = self._request("DELETE", url, headers=self._auth_headers())
        self._raise_for_status(response)
