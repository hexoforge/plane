# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.conf import settings
from django.core import signing
from django.shortcuts import redirect
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from plane.bgtasks.github_app.sync import upsert_installation
from plane.db.models import User, Workspace
from plane.utils.github_app.client import GithubAppClient

from ..base import BaseAPIView
from .base import is_github_app_configured, unsign_setup_state


class GithubSetupCallbackEndpoint(BaseAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        if not is_github_app_configured():
            return Response({"error": "not configured"}, status=status.HTTP_400_BAD_REQUEST)

        installation_id = request.GET.get("installation_id")
        state = request.GET.get("state")
        if not installation_id or not state:
            return Response({"error": "missing installation_id or state"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            data = unsign_setup_state(state)
        except signing.BadSignature:
            return Response({"error": "invalid or expired state"}, status=status.HTTP_400_BAD_REQUEST)

        workspace = Workspace.objects.filter(slug=data.get("workspace_slug")).first()
        user = User.objects.filter(id=data.get("user_id")).first()
        if not workspace or not user:
            return Response({"error": "invalid state"}, status=status.HTTP_400_BAD_REQUEST)

        client = GithubAppClient()
        installation_data = client.get_installation(int(installation_id))
        account = installation_data.get("account") or {}

        upsert_installation(
            workspace,
            user,
            installation_id=int(installation_id),
            account_login=account.get("login", ""),
            account_type=account.get("type", "User"),
            target_id=installation_data.get("target_id") or account.get("id") or 0,
        )

        redirect_url = (
            f"{settings.WEB_URL}/{workspace.slug}/settings/integrations/github/"
            f"?installation_id={installation_id}"
        )
        return redirect(redirect_url)
