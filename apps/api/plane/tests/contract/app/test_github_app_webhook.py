# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import hashlib
import hmac
import json

import pytest
from django.urls import reverse
from rest_framework import status

from plane.db.models import GithubWebhookDelivery


def _sign(body: bytes, secret: str) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


@pytest.fixture(autouse=True)
def configured_github_app(settings):
    settings.GITHUB_APP_ID = "1"
    settings.GITHUB_APP_PRIVATE_KEY = "dummy-key"
    settings.GITHUB_APP_WEBHOOK_SECRET = "whsec_test"
    settings.GITHUB_APP_SLUG = "plane-app"


@pytest.mark.contract
class TestGithubWebhookEndpoint:
    url = reverse("github-app-webhook")

    def _post(self, api_client, payload, event="ping", delivery_id="d-1", secret="whsec_test", sign=True):
        body = json.dumps(payload).encode()
        headers = {
            "HTTP_X_GITHUB_EVENT": event,
            "HTTP_X_GITHUB_DELIVERY": delivery_id,
        }
        if sign:
            headers["HTTP_X_HUB_SIGNATURE_256"] = _sign(body, secret)
        return api_client.post(self.url, data=body, content_type="application/json", **headers)

    @pytest.mark.django_db
    def test_valid_signature_is_accepted(self, api_client):
        response = self._post(api_client, {"zen": "hi"})
        assert response.status_code == status.HTTP_202_ACCEPTED
        assert GithubWebhookDelivery.objects.filter(delivery_id="d-1").exists()

    @pytest.mark.django_db
    def test_invalid_signature_is_rejected(self, api_client):
        response = self._post(api_client, {"zen": "hi"}, secret="wrong-secret")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert not GithubWebhookDelivery.objects.exists()

    @pytest.mark.django_db
    def test_missing_signature_is_rejected(self, api_client):
        response = self._post(api_client, {"zen": "hi"}, sign=False)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert not GithubWebhookDelivery.objects.exists()

    @pytest.mark.django_db
    def test_duplicate_delivery_is_reported_without_reprocessing(self, api_client):
        first = self._post(api_client, {"zen": "hi"}, delivery_id="dup-1")
        assert first.status_code == status.HTTP_202_ACCEPTED

        second = self._post(api_client, {"zen": "hi"}, delivery_id="dup-1")
        assert second.status_code == status.HTTP_200_OK
        assert second.json() == {"duplicate": True}
        assert GithubWebhookDelivery.objects.filter(delivery_id="dup-1").count() == 1

    @pytest.mark.django_db
    def test_not_configured_returns_400(self, api_client, settings):
        settings.GITHUB_APP_WEBHOOK_SECRET = None
        response = self._post(api_client, {"zen": "hi"})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_unknown_event_is_marked_skipped(self, api_client):
        response = self._post(api_client, {"zen": "hi"}, event="ping", delivery_id="ping-1")
        assert response.status_code == status.HTTP_202_ACCEPTED
        delivery = GithubWebhookDelivery.objects.get(delivery_id="ping-1")
        assert delivery.status == "skipped"
