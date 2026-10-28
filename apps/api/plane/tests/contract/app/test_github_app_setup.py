# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from unittest.mock import patch

import pytest
from django.core import signing
from django.urls import reverse
from rest_framework import status

from plane.app.views.github_app.base import sign_setup_state
from plane.db.models import GithubAppInstallation, User, WorkspaceMember


@pytest.fixture(autouse=True)
def configured_github_app(settings):
    settings.GITHUB_APP_ID = "1"
    settings.GITHUB_APP_PRIVATE_KEY = "dummy-key"
    settings.GITHUB_APP_WEBHOOK_SECRET = "whsec_test"
    settings.GITHUB_APP_SLUG = "plane-app"


@pytest.mark.contract
class TestGithubSetupCallback:
    url = reverse("github-app-setup")

    @pytest.mark.django_db
    def test_valid_state_creates_installation_and_redirects(self, api_client, workspace, create_user):
        state = sign_setup_state(workspace.slug, create_user.id)
        with patch("plane.app.views.github_app.setup.GithubAppClient") as MockClient:
            MockClient.return_value.get_installation.return_value = {
                "account": {"login": "acme", "type": "Organization", "id": 99},
                "target_id": 99,
            }
            response = api_client.get(self.url, {"installation_id": "555", "state": state})

        assert response.status_code == status.HTTP_302_FOUND
        assert f"/{workspace.slug}/settings/integrations/github/" in response["Location"]
        installation = GithubAppInstallation.objects.get(workspace=workspace)
        assert installation.installation_id == 555
        assert installation.account_login == "acme"

    @pytest.mark.django_db
    def test_client_is_called_with_installation_bound_signature(self, api_client, workspace, create_user):
        # autospec enforces the real GithubAppClient signature: installation id in
        # the constructor, get_installation() with no args. Guards the view against
        # drifting back to GithubAppClient().get_installation(id).
        state = sign_setup_state(workspace.slug, create_user.id)
        with patch("plane.app.views.github_app.setup.GithubAppClient", autospec=True) as MockClient:
            MockClient.return_value.get_installation.return_value = {
                "account": {"login": "acme", "type": "Organization", "id": 99},
                "target_id": 99,
            }
            response = api_client.get(self.url, {"installation_id": "555", "state": state})

        assert response.status_code == status.HTTP_302_FOUND
        MockClient.assert_called_once_with(555)
        MockClient.return_value.get_installation.assert_called_once_with()

    @pytest.mark.django_db
    def test_non_admin_in_state_is_forbidden(self, api_client, workspace):
        # Role could have been downgraded while the 1h-signed state was still valid.
        member = User.objects.create_user(email="member@example.com", username="member")
        WorkspaceMember.objects.create(workspace=workspace, member=member, role=15)
        state = sign_setup_state(workspace.slug, member.id)
        with patch("plane.app.views.github_app.setup.GithubAppClient", autospec=True):
            response = api_client.get(self.url, {"installation_id": "555", "state": state})
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert not GithubAppInstallation.objects.filter(workspace=workspace).exists()

    @pytest.mark.django_db
    def test_expired_state_is_rejected(self, api_client, workspace, create_user):
        state = signing.dumps(
            {"workspace_slug": workspace.slug, "user_id": str(create_user.id)},
            salt="plane.github-app.setup",
        )
        with patch("plane.app.views.github_app.setup.unsign_setup_state", side_effect=signing.SignatureExpired()):
            response = api_client.get(self.url, {"installation_id": "555", "state": state})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_tampered_state_is_rejected(self, api_client, workspace, create_user):
        response = api_client.get(self.url, {"installation_id": "555", "state": "not-a-real-signature"})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_missing_params_returns_400(self, api_client):
        response = api_client.get(self.url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
