# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Contract tests for the project wiki additions: page-collections, shares, and
the existing project pages API returning collection/sort_order and respecting
shares."""

from uuid import uuid4

import pytest
from rest_framework.test import APIClient

from plane.db.models import Page, PageCollection, PageShare, Project, ProjectMember, ProjectPage, User


def _make_project_member(workspace, project, role):
    unique_id = uuid4().hex[:8]
    user = User.objects.create(email=f"user-{unique_id}@plane.so", username=f"user_{unique_id}")
    ProjectMember.objects.create(workspace=workspace, project=project, member=user, role=role)
    client = APIClient()
    client.force_authenticate(user=user)
    return user, client


@pytest.fixture
def project(workspace, create_user):
    proj = Project.objects.create(name="Project A", identifier="PRJA", workspace=workspace)
    ProjectMember.objects.create(workspace=workspace, project=proj, member=create_user, role=20)
    return proj


def _page_collections_url(slug, project_id):
    return f"/api/workspaces/{slug}/projects/{project_id}/page-collections/"


def _pages_url(slug, project_id):
    return f"/api/workspaces/{slug}/projects/{project_id}/pages/"


def _page_detail_url(slug, project_id, page_id):
    return f"/api/workspaces/{slug}/projects/{project_id}/pages/{page_id}/"


@pytest.mark.contract
class TestProjectPageCollections:
    @pytest.mark.django_db
    def test_guest_is_forbidden(self, workspace, project):
        _, guest_client = _make_project_member(workspace, project, role=5)
        response = guest_client.get(_page_collections_url(workspace.slug, project.id))
        assert response.status_code == 403

    @pytest.mark.django_db
    def test_member_can_create_public_collection(self, workspace, project):
        _, member_client = _make_project_member(workspace, project, role=15)
        response = member_client.post(
            _page_collections_url(workspace.slug, project.id), {"name": "Runbooks"}, format="json"
        )
        assert response.status_code == 201
        assert response.data["project"] == project.id

    @pytest.mark.django_db
    def test_member_cannot_create_private_collection(self, workspace, project):
        _, member_client = _make_project_member(workspace, project, role=15)
        response = member_client.post(
            _page_collections_url(workspace.slug, project.id), {"name": "Secret", "access": 1}, format="json"
        )
        assert response.status_code == 403

    @pytest.mark.django_db
    def test_same_collection_name_allowed_in_different_project(self, session_client, workspace, project, create_user):
        session_client.post(_page_collections_url(workspace.slug, project.id), {"name": "Runbooks"}, format="json")
        other_project = Project.objects.create(name="Project B", identifier="PRJB", workspace=workspace)
        ProjectMember.objects.create(workspace=workspace, project=other_project, member=create_user, role=20)
        response = session_client.post(
            _page_collections_url(workspace.slug, other_project.id), {"name": "Runbooks"}, format="json"
        )
        assert response.status_code == 201


@pytest.mark.contract
class TestExistingProjectPagesApi:
    @pytest.mark.django_db
    def test_pages_list_returns_collection_and_sort_order(self, session_client, workspace, project, create_user):
        collection = PageCollection.objects.create(
            workspace=workspace, project=project, name="General", owned_by=create_user, is_default=True
        )
        page = Page.objects.create(
            workspace=workspace, owned_by=create_user, name="Doc", collection=collection, sort_order=42.0
        )
        ProjectPage.objects.create(workspace=workspace, project=project, page=page)

        response = session_client.get(_pages_url(workspace.slug, project.id))
        assert response.status_code == 200
        body = next(p for p in response.data if p["id"] == page.id)
        assert body["collection"] == collection.id
        assert body["sort_order"] == 42.0

    @pytest.mark.django_db
    def test_pages_list_respects_shares_for_private_pages(self, workspace, project, create_user):
        page = Page.objects.create(
            workspace=workspace, owned_by=create_user, name="Private Doc", access=Page.PRIVATE_ACCESS
        )
        ProjectPage.objects.create(workspace=workspace, project=project, page=page)

        other_user, other_client = _make_project_member(workspace, project, role=15)
        before = other_client.get(_pages_url(workspace.slug, project.id))
        assert all(p["id"] != page.id for p in before.data)

        PageShare.objects.create(page=page, user=other_user, workspace=workspace, role=PageShare.VIEW)

        after = other_client.get(_pages_url(workspace.slug, project.id))
        assert any(p["id"] == page.id for p in after.data)

    @pytest.mark.django_db
    def test_shared_user_can_retrieve_but_not_edit_with_view_role(self, workspace, project, create_user):
        page = Page.objects.create(
            workspace=workspace, owned_by=create_user, name="Private Doc", access=Page.PRIVATE_ACCESS
        )
        ProjectPage.objects.create(workspace=workspace, project=project, page=page)

        other_user, other_client = _make_project_member(workspace, project, role=15)
        denied = other_client.get(_page_detail_url(workspace.slug, project.id, page.id))
        assert denied.status_code == 403

        PageShare.objects.create(page=page, user=other_user, workspace=workspace, role=PageShare.VIEW)
        allowed = other_client.get(_page_detail_url(workspace.slug, project.id, page.id))
        assert allowed.status_code == 200

        edit_denied = other_client.patch(
            _page_detail_url(workspace.slug, project.id, page.id), {"name": "Hacked"}, format="json"
        )
        assert edit_denied.status_code == 403


@pytest.mark.contract
class TestProjectPageShares:
    @pytest.mark.django_db
    def test_only_owner_can_create_share(self, workspace, project, create_user):
        member_user, member_client = _make_project_member(workspace, project, role=15)
        page = Page.objects.create(
            workspace=workspace, owned_by=member_user, name="Member Doc", access=Page.PRIVATE_ACCESS
        )
        ProjectPage.objects.create(workspace=workspace, project=project, page=page)

        other_user, other_client = _make_project_member(workspace, project, role=20)
        denied = other_client.post(
            f"/api/workspaces/{workspace.slug}/projects/{project.id}/pages/{page.id}/shares/",
            {"user": str(other_user.id), "role": PageShare.VIEW},
            format="json",
        )
        assert denied.status_code == 403

        allowed = member_client.post(
            f"/api/workspaces/{workspace.slug}/projects/{project.id}/pages/{page.id}/shares/",
            {"user": str(other_user.id), "role": PageShare.VIEW},
            format="json",
        )
        assert allowed.status_code == 201
