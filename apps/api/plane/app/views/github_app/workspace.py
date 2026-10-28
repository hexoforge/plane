# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.conf import settings
from rest_framework import status
from rest_framework.response import Response

from plane.app.permissions import ROLE, allow_permission
from plane.bgtasks.github_app.sync import upsert_installation
from plane.db.models import GithubAppInstallation, GithubLinkedRepository, Workspace
from plane.utils.github_app.client import GithubAppClient

from ..base import BaseAPIView
from .base import is_github_app_configured, require_github_app, sign_setup_state


class GithubWorkspaceIntegrationEndpoint(BaseAPIView):
    @allow_permission(allowed_roles=[ROLE.ADMIN], level="WORKSPACE")
    def get(self, request, slug):
        configured = is_github_app_configured()
        install_url = None
        installation_data = None

        if configured:
            install_url = (
                f"https://github.com/apps/{settings.GITHUB_APP_SLUG}/installations/new"
                f"?state={sign_setup_state(slug, request.user.id)}"
            )
            installation = GithubAppInstallation.objects.filter(workspace__slug=slug).first()
            if installation:
                installation_data = {
                    "installation_id": installation.installation_id,
                    "account_login": installation.account_login,
                    "account_type": installation.account_type,
                    "suspended": installation.suspended_at is not None,
                }

        return Response(
            {
                "configured": configured,
                "app_slug": settings.GITHUB_APP_SLUG,
                "install_url": install_url,
                "installation": installation_data,
            },
            status=status.HTTP_200_OK,
        )


class GithubWorkspaceInstallationEndpoint(BaseAPIView):
    @allow_permission(allowed_roles=[ROLE.ADMIN], level="WORKSPACE")
    @require_github_app
    def post(self, request, slug):
        installation_id = request.data.get("installation_id")
        if not installation_id:
            return Response({"error": "installation_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        workspace = Workspace.objects.get(slug=slug)
        client = GithubAppClient(int(installation_id))
        installation_data = client.get_installation()
        account = installation_data.get("account") or {}

        installation = upsert_installation(
            workspace,
            request.user,
            installation_id=int(installation_id),
            account_login=account.get("login", ""),
            account_type=account.get("type", "User"),
            target_id=installation_data.get("target_id") or account.get("id") or 0,
        )
        return Response(
            {"installation_id": installation.installation_id, "account_login": installation.account_login},
            status=status.HTTP_201_CREATED,
        )

    @allow_permission(allowed_roles=[ROLE.ADMIN], level="WORKSPACE")
    @require_github_app
    def delete(self, request, slug):
        installation = GithubAppInstallation.objects.filter(workspace__slug=slug).first()
        if not installation:
            return Response(status=status.HTTP_204_NO_CONTENT)

        GithubLinkedRepository.objects.filter(installation=installation).update(is_active=False)
        installation.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class GithubWorkspaceRepositoriesEndpoint(BaseAPIView):
    @allow_permission(allowed_roles=[ROLE.ADMIN], level="WORKSPACE")
    @require_github_app
    def get(self, request, slug):
        installation = GithubAppInstallation.objects.filter(workspace__slug=slug).first()
        if not installation:
            return Response({"error": "no installation"}, status=status.HTTP_400_BAD_REQUEST)

        client = GithubAppClient(installation.installation_id)
        repos = client.list_installation_repos()
        linked_project_by_repo_id = {
            link.repo_id: str(link.project_id)
            for link in GithubLinkedRepository.objects.filter(workspace__slug=slug, is_active=True)
        }

        data = [
            {
                "id": repo.get("id"),
                "full_name": repo.get("full_name"),
                "private": repo.get("private", False),
                "html_url": repo.get("html_url"),
                "default_branch": repo.get("default_branch"),
                "linked_project_id": linked_project_by_repo_id.get(repo.get("id")),
            }
            for repo in repos
        ]
        return Response(data, status=status.HTTP_200_OK)
