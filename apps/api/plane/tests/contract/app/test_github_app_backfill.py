# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework import status

from plane.db.models import (
    GithubAppInstallation,
    GithubBackfillRun,
    GithubLinkedRepository,
    Project,
    ProjectMember,
    State,
    User,
    WorkspaceMember,
)


@pytest.fixture(autouse=True)
def configured_github_app(settings):
    settings.GITHUB_APP_ID = "1"
    settings.GITHUB_APP_PRIVATE_KEY = "dummy-key"
    settings.GITHUB_APP_WEBHOOK_SECRET = "whsec_test"
    settings.GITHUB_APP_SLUG = "plane-app"


@pytest.fixture
def project(db, workspace, create_user):
    project = Project.objects.create(
        name="Github Project", identifier="GH", workspace=workspace, created_by=create_user
    )
    ProjectMember.objects.create(project=project, member=create_user, workspace=workspace, role=20)
    State.objects.create(name="Backlog", project=project, group="backlog", default=True)
    return project


@pytest.fixture
def installation(db, workspace, create_user):
    return GithubAppInstallation.objects.create(
        workspace=workspace,
        installation_id=42,
        account_login="acme",
        account_type="Organization",
        target_id=1,
        installed_by=create_user,
    )


@pytest.fixture
def linked_repo(project, installation):
    return GithubLinkedRepository.objects.create(
        project=project,
        installation=installation,
        repo_id=1,
        full_name="acme/widgets",
        html_url="https://github.com/acme/widgets",
    )


@pytest.fixture
def member_user(db, workspace, project):
    user = User.objects.create_user(email="member@example.com", username="member")
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=15)
    ProjectMember.objects.create(project=project, member=user, workspace=workspace, role=15)
    return user


def backfill_url(workspace, project, linked_repo):
    return reverse(
        "project-github-repository-backfill",
        kwargs={"slug": workspace.slug, "project_id": project.id, "pk": linked_repo.id},
    )


@pytest.mark.contract
class TestGithubBackfillPermissions:
    @pytest.mark.django_db
    def test_admin_can_start_a_backfill(self, session_client, workspace, project, linked_repo):
        with patch("plane.bgtasks.github_app.backfill.run_github_backfill.delay") as mock_delay:
            response = session_client.post(backfill_url(workspace, project, linked_repo), {}, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["status"] == "queued"
        mock_delay.assert_called_once()

    @pytest.mark.django_db
    def test_member_cannot_start_a_backfill(self, session_client, workspace, project, linked_repo, member_user):
        session_client.force_authenticate(user=member_user)
        response = session_client.post(backfill_url(workspace, project, linked_repo), {}, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.django_db
    def test_member_cannot_view_backfill_status(self, session_client, workspace, project, linked_repo, member_user):
        session_client.force_authenticate(user=member_user)
        response = session_client.get(backfill_url(workspace, project, linked_repo))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.django_db
    def test_admin_can_view_backfill_status(self, session_client, workspace, project, linked_repo):
        GithubBackfillRun.objects.create(project=project, linked_repo=linked_repo, status="completed")
        response = session_client.get(backfill_url(workspace, project, linked_repo))
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "completed"

    @pytest.mark.django_db
    def test_status_is_null_when_no_run_exists_yet(self, session_client, workspace, project, linked_repo):
        response = session_client.get(backfill_url(workspace, project, linked_repo))
        assert response.status_code == status.HTTP_200_OK
        assert response.data is None


@pytest.mark.contract
class TestGithubBackfillOneActiveRun:
    @pytest.mark.django_db
    def test_starting_a_second_backfill_while_one_is_active_returns_409(
        self, session_client, workspace, project, linked_repo
    ):
        with patch("plane.bgtasks.github_app.backfill.run_github_backfill.delay"):
            first = session_client.post(backfill_url(workspace, project, linked_repo), {}, format="json")
        assert first.status_code == status.HTTP_201_CREATED

        with patch("plane.bgtasks.github_app.backfill.run_github_backfill.delay"):
            second = session_client.post(backfill_url(workspace, project, linked_repo), {}, format="json")
        assert second.status_code == status.HTTP_409_CONFLICT

    @pytest.mark.django_db
    def test_new_backfill_allowed_once_previous_one_completed(
        self, session_client, workspace, project, linked_repo
    ):
        GithubBackfillRun.objects.create(project=project, linked_repo=linked_repo, status="completed")
        with patch("plane.bgtasks.github_app.backfill.run_github_backfill.delay") as mock_delay:
            response = session_client.post(backfill_url(workspace, project, linked_repo), {}, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        mock_delay.assert_called_once()
