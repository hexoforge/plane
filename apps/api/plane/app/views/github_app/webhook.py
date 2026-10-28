# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import json

from django.conf import settings
from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from plane.bgtasks.github_app.process_delivery import process_github_delivery
from plane.db.models import GithubWebhookDelivery
from plane.utils.github_app.signature import verify_signature

from ..base import BaseAPIView
from .base import is_github_app_configured


class GithubWebhookEndpoint(BaseAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        if not is_github_app_configured():
            return Response({"error": "not configured"}, status=status.HTTP_400_BAD_REQUEST)

        raw_body = request.body
        signature_header = request.META.get("HTTP_X_HUB_SIGNATURE_256")
        if not verify_signature(raw_body, signature_header, settings.GITHUB_APP_WEBHOOK_SECRET):
            return Response({"error": "invalid signature"}, status=status.HTTP_401_UNAUTHORIZED)

        delivery_id = request.META.get("HTTP_X_GITHUB_DELIVERY")
        event = request.META.get("HTTP_X_GITHUB_EVENT")
        if not delivery_id or not event:
            return Response({"error": "missing delivery headers"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            payload = json.loads(raw_body or b"{}")
        except ValueError:
            return Response({"error": "invalid payload"}, status=status.HTTP_400_BAD_REQUEST)

        installation_id = (payload.get("installation") or {}).get("id")

        try:
            # Isolated in its own savepoint so a duplicate-key error here
            # can't poison a surrounding transaction (e.g. under
            # ATOMIC_REQUESTS or a test's transactional wrapper).
            with transaction.atomic():
                delivery = GithubWebhookDelivery.objects.create(
                    delivery_id=delivery_id,
                    event=event,
                    action=payload.get("action"),
                    installation_id=installation_id,
                    payload=payload,
                    status="received",
                )
        except IntegrityError:
            return Response({"duplicate": True}, status=status.HTTP_200_OK)

        process_github_delivery.delay(str(delivery.id))
        return Response({"status": "accepted"}, status=status.HTTP_202_ACCEPTED)
