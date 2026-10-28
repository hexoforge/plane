# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Contract tests for the company wiki endpoints under /api/workspaces/<slug>/wiki/."""

from uuid import uuid4

import pytest
from rest_framework.test import APIClient

from plane.db.models import Page, PageCollection, PageShare, User, WorkspaceMember


def _make_member(workspace, role):
    unique_id = uuid4().hex[:8]
    user = User.objects.create(email=f"user-{unique_id}@plane.so", username=f"user_{unique_id}")
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=role)
    client = APIClient()
    client.force_authenticate(user=user)
    return user, client


def _collections_url(slug):
    return f"/api/workspaces/{slug}/wiki/collections/"


def _pages_url(slug):
    return f"/api/workspaces/{slug}/wiki/pages/"


def _page_detail_url(slug, page_id):
    return f"/api/workspaces/{slug}/wiki/pages/{page_id}/"


def _create_public_collection(workspace, client):
    response = client.post(_collections_url(workspace.slug), {"name": f"Collection {uuid4().hex[:6]}"}, format="json")
    assert response.status_code == 201, response.data
    return response.data["id"]


@pytest.mark.contract
class TestWikiCollections:
    @pytest.mark.django_db
    def test_guest_is_forbidden(self, workspace):
        _, guest_client = _make_member(workspace, role=5)
        response = guest_client.get(_collections_url(workspace.slug))
        assert response.status_code == 403

    @pytest.mark.django_db
    def test_member_can_create_public_collection(self, workspace):
        _, member_client = _make_member(workspace, role=15)
        response = member_client.post(_collections_url(workspace.slug), {"name": "Engineering"}, format="json")
        assert response.status_code == 201
        assert response.data["access"] == PageCollection.PUBLIC_ACCESS

    @pytest.mark.django_db
    def test_member_cannot_create_private_collection(self, workspace):
        _, member_client = _make_member(workspace, role=15)
        response = member_client.post(
            _collections_url(workspace.slug), {"name": "Secret", "access": 1}, format="json"
        )
        assert response.status_code == 403

    @pytest.mark.django_db
    def test_admin_can_create_private_collection(self, session_client, workspace):
        # The `workspace` fixture makes create_user an Admin (role=20).
        response = session_client.post(
            _collections_url(workspace.slug), {"name": "Leadership", "access": 1}, format="json"
        )
        assert response.status_code == 201
        assert response.data["access"] == PageCollection.PRIVATE_ACCESS

    @pytest.mark.django_db
    def test_private_collection_hidden_from_other_members(self, session_client, workspace):
        session_client.post(_collections_url(workspace.slug), {"name": "Leadership", "access": 1}, format="json")
        _, member_client = _make_member(workspace, role=15)
        response = member_client.get(_collections_url(workspace.slug))
        assert response.status_code == 200
        assert all(c["name"] != "Leadership" for c in response.data)

    @pytest.mark.django_db
    def test_default_collection_cannot_be_deleted(self, workspace, create_user, session_client):
        collection = PageCollection.objects.create(
            workspace=workspace, project=None, name="General", owned_by=create_user, is_default=True
        )
        response = session_client.delete(f"{_collections_url(workspace.slug)}{collection.id}/")
        assert response.status_code == 400


@pytest.mark.contract
class TestWikiPages:
    @pytest.mark.django_db
    def test_guest_is_forbidden(self, workspace):
        _, guest_client = _make_member(workspace, role=5)
        response = guest_client.get(_pages_url(workspace.slug))
        assert response.status_code == 403

    @pytest.mark.django_db
    def test_create_page_requires_collection(self, session_client, workspace):
        response = session_client.post(_pages_url(workspace.slug), {"name": "Doc"}, format="json")
        assert response.status_code == 400

    @pytest.mark.django_db
    def test_member_can_create_public_page(self, workspace):
        _, member_client = _make_member(workspace, role=15)
        collection_id = _create_public_collection(workspace, member_client)
        response = member_client.post(
            _pages_url(workspace.slug), {"name": "Onboarding", "collection": collection_id}, format="json"
        )
        assert response.status_code == 201
        assert response.data["collection"] == collection_id

    @pytest.mark.django_db
    def test_private_page_hidden_from_other_members_until_shared(self, session_client, workspace):
        collection_id = _create_public_collection(workspace, session_client)
        create_response = session_client.post(
            _pages_url(workspace.slug),
            {"name": "Secret Doc", "collection": collection_id, "access": Page.PRIVATE_ACCESS},
            format="json",
        )
        assert create_response.status_code == 201
        page_id = create_response.data["id"]

        other_user, other_client = _make_member(workspace, role=15)
        denied = other_client.get(_page_detail_url(workspace.slug, page_id))
        assert denied.status_code == 403

        page = Page.objects.get(pk=page_id)
        PageShare.objects.create(page=page, user=other_user, workspace=workspace, role=PageShare.VIEW)

        allowed = other_client.get(_page_detail_url(workspace.slug, page_id))
        assert allowed.status_code == 200

        view_only_edit = other_client.patch(
            _page_detail_url(workspace.slug, page_id), {"name": "Hacked"}, format="json"
        )
        assert view_only_edit.status_code == 403

        PageShare.objects.filter(page=page, user=other_user).update(role=PageShare.EDIT)
        edit_allowed = other_client.patch(
            _page_detail_url(workspace.slug, page_id), {"name": "Edited by collaborator"}, format="json"
        )
        assert edit_allowed.status_code == 200

    @pytest.mark.django_db
    def test_only_owner_can_create_share_not_just_admin(self, session_client, workspace):
        """Design: 'only owner can share/delete/change access' -- an admin who
        does not own the page must not be able to manage its shares."""
        member_user, member_client = _make_member(workspace, role=15)
        collection_id = _create_public_collection(workspace, member_client)
        create_response = member_client.post(
            _pages_url(workspace.slug),
            {"name": "Member's Doc", "collection": collection_id, "access": Page.PRIVATE_ACCESS},
            format="json",
        )
        page_id = create_response.data["id"]

        # session_client is an Admin (not the page owner) in this workspace.
        response = session_client.post(
            f"/api/workspaces/{workspace.slug}/wiki/pages/{page_id}/shares/",
            {"user": str(member_user.id), "role": PageShare.VIEW},
            format="json",
        )
        assert response.status_code == 403

    @pytest.mark.django_db
    def test_search_filters_by_name(self, session_client, workspace):
        collection_id = _create_public_collection(workspace, session_client)
        session_client.post(
            _pages_url(workspace.slug), {"name": "Alpha Doc", "collection": collection_id}, format="json"
        )
        session_client.post(
            _pages_url(workspace.slug), {"name": "Beta Doc", "collection": collection_id}, format="json"
        )

        response = session_client.get(_pages_url(workspace.slug), {"search": "Alpha"})
        assert response.status_code == 200
        names = [p["name"] for p in response.data]
        assert names == ["Alpha Doc"]

    @pytest.mark.django_db
    def test_archive_and_unarchive(self, session_client, workspace):
        collection_id = _create_public_collection(workspace, session_client)
        create_response = session_client.post(
            _pages_url(workspace.slug), {"name": "Archivable", "collection": collection_id}, format="json"
        )
        page_id = create_response.data["id"]

        archive_response = session_client.post(f"{_page_detail_url(workspace.slug, page_id)}archive/")
        assert archive_response.status_code == 200

        active_list = session_client.get(_pages_url(workspace.slug))
        assert all(p["id"] != page_id for p in active_list.data)

        archived_list = session_client.get(_pages_url(workspace.slug), {"archived": "true"})
        assert any(p["id"] == page_id for p in archived_list.data)

        unarchive_response = session_client.delete(f"{_page_detail_url(workspace.slug, page_id)}archive/")
        assert unarchive_response.status_code == 204

        active_list_after = session_client.get(_pages_url(workspace.slug))
        assert any(p["id"] == page_id for p in active_list_after.data)


@pytest.mark.contract
class TestWikiComments:
    @pytest.mark.django_db
    def test_view_only_share_cannot_comment(self, session_client, workspace):
        collection_id = _create_public_collection(workspace, session_client)
        create_response = session_client.post(
            _pages_url(workspace.slug),
            {"name": "Private Doc", "collection": collection_id, "access": Page.PRIVATE_ACCESS},
            format="json",
        )
        page_id = create_response.data["id"]
        page = Page.objects.get(pk=page_id)

        other_user, other_client = _make_member(workspace, role=15)
        PageShare.objects.create(page=page, user=other_user, workspace=workspace, role=PageShare.VIEW)

        denied = other_client.post(
            f"/api/workspaces/{workspace.slug}/wiki/pages/{page_id}/comments/",
            {"comment_html": "<p>nice</p>"},
            format="json",
        )
        assert denied.status_code == 403

        PageShare.objects.filter(page=page, user=other_user).update(role=PageShare.COMMENT)
        allowed = other_client.post(
            f"/api/workspaces/{workspace.slug}/wiki/pages/{page_id}/comments/",
            {"comment_html": "<p>nice</p>"},
            format="json",
        )
        assert allowed.status_code == 201

    @pytest.mark.django_db
    def test_author_can_edit_and_delete_comment_via_flat_route(self, session_client, workspace):
        """The flat comments/<pk>/ route carries no page_id; the author must still
        be able to edit and delete their own comment."""
        collection_id = _create_public_collection(workspace, session_client)
        page_id = session_client.post(
            _pages_url(workspace.slug), {"name": "Doc", "collection": collection_id}, format="json"
        ).data["id"]

        comment_id = session_client.post(
            f"/api/workspaces/{workspace.slug}/wiki/pages/{page_id}/comments/",
            {"comment_html": "<p>first</p>"},
            format="json",
        ).data["id"]

        edited = session_client.patch(
            f"/api/workspaces/{workspace.slug}/wiki/comments/{comment_id}/",
            {"comment_html": "<p>edited</p>"},
            format="json",
        )
        assert edited.status_code == 200, edited.data

        deleted = session_client.delete(f"/api/workspaces/{workspace.slug}/wiki/comments/{comment_id}/")
        assert deleted.status_code == 204

    @pytest.mark.django_db
    def test_non_author_member_cannot_edit_comment_via_flat_route(self, session_client, workspace):
        collection_id = _create_public_collection(workspace, session_client)
        page_id = session_client.post(
            _pages_url(workspace.slug), {"name": "Doc", "collection": collection_id}, format="json"
        ).data["id"]
        comment_id = session_client.post(
            f"/api/workspaces/{workspace.slug}/wiki/pages/{page_id}/comments/",
            {"comment_html": "<p>owner comment</p>"},
            format="json",
        ).data["id"]

        _, member_client = _make_member(workspace, role=15)
        response = member_client.patch(
            f"/api/workspaces/{workspace.slug}/wiki/comments/{comment_id}/",
            {"comment_html": "<p>tampered</p>"},
            format="json",
        )
        assert response.status_code == 403


@pytest.mark.contract
class TestWikiPageDescription:
    @pytest.mark.django_db
    def test_shared_user_can_fetch_private_page_description(self, session_client, workspace):
        """A user with a share on a private page must be able to load its binary
        description (used by the collaborative editor), not get a 404/500."""
        collection_id = _create_public_collection(workspace, session_client)
        page_id = session_client.post(
            _pages_url(workspace.slug),
            {"name": "Secret", "collection": collection_id, "access": Page.PRIVATE_ACCESS},
            format="json",
        ).data["id"]
        page = Page.objects.get(pk=page_id)

        other_user, other_client = _make_member(workspace, role=15)
        description_url = f"/api/workspaces/{workspace.slug}/wiki/pages/{page_id}/description/"

        denied = other_client.get(description_url)
        assert denied.status_code == 403

        PageShare.objects.create(page=page, user=other_user, workspace=workspace, role=PageShare.VIEW)
        allowed = other_client.get(description_url)
        assert allowed.status_code == 200


@pytest.mark.contract
class TestWikiTree:
    @pytest.mark.django_db
    def test_tree_returns_collections_and_pages(self, session_client, workspace):
        collection_id = _create_public_collection(workspace, session_client)
        session_client.post(_pages_url(workspace.slug), {"name": "Doc", "collection": collection_id}, format="json")

        response = session_client.get(f"/api/workspaces/{workspace.slug}/wiki/tree/")
        assert response.status_code == 200
        assert any(c["id"] == collection_id for c in response.data["collections"])
        assert any(p["name"] == "Doc" for p in response.data["pages"])
