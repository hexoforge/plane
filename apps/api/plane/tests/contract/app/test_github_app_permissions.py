# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from plane.db.models import (
    GithubAppInstallation,
    GithubIssueLink,
    GithubLinkedRepository,
    GithubPullRequestLink,
    Issue,
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
def member_user(db, workspace, project):
    user = User.objects.create_user(email="member@example.com", username="member")
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=15)
    ProjectMember.objects.create(project=project, member=user, workspace=workspace, role=15)
    return user


@pytest.fixture
def guest_user(db, workspace, project):
    user = User.objects.create_user(email="guest@example.com", username="guest")
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=5)
    ProjectMember.objects.create(project=project, member=user, workspace=workspace, role=5)
    return user


@pytest.mark.contract
class TestWorkspaceIntegrationPermissions:
    @pytest.mark.django_db
    def test_admin_can_view_status(self, session_client, workspace):
        url = reverse("workspace-github-integration", kwargs={"slug": workspace.slug})
        response = session_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["configured"] is True

    @pytest.mark.django_db
    def test_member_is_forbidden(self, session_client, workspace, project, member_user):
        session_client.force_authenticate(user=member_user)
        url = reverse("workspace-github-integration", kwargs={"slug": workspace.slug})
        response = session_client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.django_db
    def test_guest_is_forbidden(self, session_client, workspace, project, guest_user):
        session_client.force_authenticate(user=guest_user)
        url = reverse("workspace-github-integration", kwargs={"slug": workspace.slug})
        response = session_client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.django_db
    def test_admin_can_disconnect_installation(self, session_client, workspace, create_user):
        GithubAppInstallation.objects.create(
            workspace=workspace,
            installation_id=42,
            account_login="acme",
            account_type="Organization",
            target_id=1,
            installed_by=create_user,
        )
        url = reverse("workspace-github-installation", kwargs={"slug": workspace.slug})
        response = session_client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not GithubAppInstallation.objects.filter(workspace=workspace).exists()


@pytest.mark.contract
class TestProjectRepositoriesPermissions:
    @pytest.mark.django_db
    def test_admin_can_list_repositories(self, session_client, workspace, project):
        url = reverse("project-github-repositories", kwargs={"slug": workspace.slug, "project_id": project.id})
        response = session_client.get(url)
        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.django_db
    def test_member_can_list_repositories(self, session_client, workspace, project, member_user):
        session_client.force_authenticate(user=member_user)
        url = reverse("project-github-repositories", kwargs={"slug": workspace.slug, "project_id": project.id})
        response = session_client.get(url)
        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.django_db
    def test_guest_is_forbidden_from_repository_list(self, session_client, workspace, project, guest_user):
        session_client.force_authenticate(user=guest_user)
        url = reverse("project-github-repositories", kwargs={"slug": workspace.slug, "project_id": project.id})
        response = session_client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.django_db
    def test_member_cannot_link_repository(self, session_client, workspace, project, member_user):
        session_client.force_authenticate(user=member_user)
        url = reverse("project-github-repositories", kwargs={"slug": workspace.slug, "project_id": project.id})
        response = session_client.post(url, {"repo_id": 1, "full_name": "acme/widgets"}, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.django_db
    def test_admin_can_link_repository(self, session_client, workspace, project, create_user):
        GithubAppInstallation.objects.create(
            workspace=workspace,
            installation_id=42,
            account_login="acme",
            account_type="Organization",
            target_id=1,
            installed_by=create_user,
        )
        url = reverse("project-github-repositories", kwargs={"slug": workspace.slug, "project_id": project.id})
        response = session_client.post(
            url, {"repo_id": 1, "full_name": "acme/widgets", "html_url": "https://github.com/acme/widgets"}, format="json"
        )
        assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.contract
class TestProjectStateMappingPermissions:
    @pytest.mark.django_db
    def test_member_can_read(self, session_client, workspace, project, member_user):
        session_client.force_authenticate(user=member_user)
        url = reverse("project-github-state-mapping", kwargs={"slug": workspace.slug, "project_id": project.id})
        response = session_client.get(url)
        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.django_db
    def test_guest_cannot_read(self, session_client, workspace, project, guest_user):
        session_client.force_authenticate(user=guest_user)
        url = reverse("project-github-state-mapping", kwargs={"slug": workspace.slug, "project_id": project.id})
        response = session_client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.django_db
    def test_member_cannot_write(self, session_client, workspace, project, member_user):
        session_client.force_authenticate(user=member_user)
        url = reverse("project-github-state-mapping", kwargs={"slug": workspace.slug, "project_id": project.id})
        response = session_client.put(url, {"auto_create_issues": False}, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.django_db
    def test_admin_can_write(self, session_client, workspace, project):
        url = reverse("project-github-state-mapping", kwargs={"slug": workspace.slug, "project_id": project.id})
        response = session_client.put(url, {"auto_create_issues": False}, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["auto_create_issues"] is False


@pytest.mark.contract
class TestIssueGithubDetailPermissions:
    @pytest.fixture
    def issue(self, db, project):
        state = State.objects.get(project=project, group="backlog")
        return Issue.objects.create(project=project, name="Something broke", state=state)

    @pytest.fixture
    def installation(self, db, workspace, create_user):
        return GithubAppInstallation.objects.create(
            workspace=workspace,
            installation_id=42,
            account_login="acme",
            account_type="Organization",
            target_id=1,
            installed_by=create_user,
        )

    def _linked_repo(self, project, installation, private):
        return GithubLinkedRepository.objects.create(
            project=project,
            installation=installation,
            repo_id=1,
            full_name="acme/widgets",
            private=private,
            html_url="https://github.com/acme/widgets",
        )

    @pytest.mark.django_db
    def test_guest_can_view_public_repo_prs(self, session_client, workspace, project, issue, installation, guest_user):
        linked_repo = self._linked_repo(project, installation, private=False)
        GithubPullRequestLink.objects.create(
            project=project,
            issue=issue,
            linked_repo=linked_repo,
            pr_id=1,
            pr_number=1,
            title="PR",
            url="https://github.com/acme/widgets/pull/1",
            state="open",
            gh_updated_at=timezone.now(),
        )
        session_client.force_authenticate(user=guest_user)
        url = reverse(
            "issue-github-detail", kwargs={"slug": workspace.slug, "project_id": project.id, "issue_id": issue.id}
        )
        response = session_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["pull_requests"]) == 1

    @pytest.mark.django_db
    def test_guest_is_forbidden_when_repo_is_private(
        self, session_client, workspace, project, issue, installation, guest_user
    ):
        linked_repo = self._linked_repo(project, installation, private=True)
        GithubPullRequestLink.objects.create(
            project=project,
            issue=issue,
            linked_repo=linked_repo,
            pr_id=1,
            pr_number=1,
            title="PR",
            url="https://github.com/acme/widgets/pull/1",
            state="open",
            gh_updated_at=timezone.now(),
        )
        session_client.force_authenticate(user=guest_user)
        url = reverse(
            "issue-github-detail", kwargs={"slug": workspace.slug, "project_id": project.id, "issue_id": issue.id}
        )
        response = session_client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.django_db
    def test_member_can_view_private_repo(
        self, session_client, workspace, project, issue, installation, member_user
    ):
        linked_repo = self._linked_repo(project, installation, private=True)
        GithubIssueLink.objects.create(
            project=project,
            issue=issue,
            linked_repo=linked_repo,
            gh_issue_id=1,
            gh_issue_number=1,
            url="https://github.com/acme/widgets/issues/1",
            gh_state="open",
            gh_updated_at=timezone.now(),
        )
        session_client.force_authenticate(user=member_user)
        url = reverse(
            "issue-github-detail", kwargs={"slug": workspace.slug, "project_id": project.id, "issue_id": issue.id}
        )
        response = session_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["issue_link"] is not None
