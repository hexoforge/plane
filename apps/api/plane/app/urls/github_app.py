# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.urls import path

from plane.app.views import (
    GithubIssueDetailEndpoint,
    GithubProjectRepositoriesEndpoint,
    GithubProjectStateMappingEndpoint,
    GithubSetupCallbackEndpoint,
    GithubWebhookEndpoint,
    GithubWorkspaceInstallationEndpoint,
    GithubWorkspaceIntegrationEndpoint,
    GithubWorkspaceRepositoriesEndpoint,
)

urlpatterns = [
    path(
        "workspaces/<str:slug>/integrations/github/",
        GithubWorkspaceIntegrationEndpoint.as_view(),
        name="workspace-github-integration",
    ),
    path(
        "workspaces/<str:slug>/integrations/github/installation/",
        GithubWorkspaceInstallationEndpoint.as_view(),
        name="workspace-github-installation",
    ),
    path(
        "workspaces/<str:slug>/integrations/github/repositories/",
        GithubWorkspaceRepositoriesEndpoint.as_view(),
        name="workspace-github-repositories",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/github/repositories/",
        GithubProjectRepositoriesEndpoint.as_view(),
        name="project-github-repositories",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/github/repositories/<uuid:pk>/",
        GithubProjectRepositoriesEndpoint.as_view(),
        name="project-github-repository",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/github/state-mapping/",
        GithubProjectStateMappingEndpoint.as_view(),
        name="project-github-state-mapping",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/issues/<uuid:issue_id>/github/",
        GithubIssueDetailEndpoint.as_view(),
        name="issue-github-detail",
    ),
    path(
        "integrations/github/setup/",
        GithubSetupCallbackEndpoint.as_view(),
        name="github-app-setup",
    ),
    path(
        "integrations/github/webhook/",
        GithubWebhookEndpoint.as_view(),
        name="github-app-webhook",
    ),
]
