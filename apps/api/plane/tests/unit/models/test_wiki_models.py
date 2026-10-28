# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import pytest
from django.db import IntegrityError, transaction

from plane.db.models import Page, PageCollection, PageComment, PageShare, Project


@pytest.mark.unit
class TestPageCollectionModel:
    @pytest.mark.django_db
    def test_company_default_collection_creation(self, workspace, create_user):
        collection = PageCollection.objects.create(
            workspace=workspace, project=None, name="General", owned_by=create_user, is_default=True
        )
        assert collection.project is None
        assert collection.access == PageCollection.PUBLIC_ACCESS

    @pytest.mark.django_db
    def test_duplicate_name_same_workspace_no_project_rejected(self, workspace, create_user):
        PageCollection.objects.create(workspace=workspace, project=None, name="Engineering", owned_by=create_user)
        with pytest.raises(IntegrityError), transaction.atomic():
            PageCollection.objects.create(workspace=workspace, project=None, name="Engineering", owned_by=create_user)

    @pytest.mark.django_db
    def test_duplicate_name_same_project_rejected(self, workspace, create_user):
        project = Project.objects.create(name="Proj A", identifier="PRJA", workspace=workspace)
        PageCollection.objects.create(workspace=workspace, project=project, name="Engineering", owned_by=create_user)
        with pytest.raises(IntegrityError), transaction.atomic():
            PageCollection.objects.create(
                workspace=workspace, project=project, name="Engineering", owned_by=create_user
            )

    @pytest.mark.django_db
    def test_same_name_allowed_across_different_projects(self, workspace, create_user):
        project_a = Project.objects.create(name="Proj A", identifier="PRJA", workspace=workspace)
        project_b = Project.objects.create(name="Proj B", identifier="PRJB", workspace=workspace)
        PageCollection.objects.create(workspace=workspace, project=project_a, name="Engineering", owned_by=create_user)
        # No IntegrityError expected: unique constraint is scoped per project.
        PageCollection.objects.create(workspace=workspace, project=project_b, name="Engineering", owned_by=create_user)

    @pytest.mark.django_db
    def test_only_one_default_collection_per_workspace(self, workspace, create_user):
        PageCollection.objects.create(
            workspace=workspace, project=None, name="General", owned_by=create_user, is_default=True
        )
        with pytest.raises(IntegrityError), transaction.atomic():
            PageCollection.objects.create(
                workspace=workspace, project=None, name="Other", owned_by=create_user, is_default=True
            )

    @pytest.mark.django_db
    def test_only_one_default_collection_per_project(self, workspace, create_user):
        project = Project.objects.create(name="Proj A", identifier="PRJA", workspace=workspace)
        PageCollection.objects.create(
            workspace=workspace, project=project, name="General", owned_by=create_user, is_default=True
        )
        with pytest.raises(IntegrityError), transaction.atomic():
            PageCollection.objects.create(
                workspace=workspace, project=project, name="Other", owned_by=create_user, is_default=True
            )

    @pytest.mark.django_db
    def test_page_collection_set_null_on_collection_delete(self, workspace, create_user):
        collection = PageCollection.objects.create(
            workspace=workspace, project=None, name="General", owned_by=create_user
        )
        page = Page.objects.create(workspace=workspace, owned_by=create_user, name="Doc", collection=collection)

        # A hard delete (soft=False) exercises the real on_delete=SET_NULL FK
        # behavior; Plane's default soft-delete just stamps deleted_at and
        # leaves related rows untouched.
        collection.delete(soft=False)
        page.refresh_from_db()
        assert page.collection_id is None


@pytest.mark.unit
class TestPageShareModel:
    @pytest.mark.django_db
    def test_share_creation(self, workspace, create_user):
        page = Page.objects.create(workspace=workspace, owned_by=create_user, name="Doc", access=Page.PRIVATE_ACCESS)
        other_user = _make_user("shared-user")
        share = PageShare.objects.create(page=page, user=other_user, workspace=workspace, role=PageShare.VIEW)
        assert share.role == PageShare.VIEW

    @pytest.mark.django_db
    def test_duplicate_share_for_same_user_rejected(self, workspace, create_user):
        page = Page.objects.create(workspace=workspace, owned_by=create_user, name="Doc", access=Page.PRIVATE_ACCESS)
        other_user = _make_user("shared-user-2")
        PageShare.objects.create(page=page, user=other_user, workspace=workspace, role=PageShare.VIEW)
        with pytest.raises(IntegrityError), transaction.atomic():
            PageShare.objects.create(page=page, user=other_user, workspace=workspace, role=PageShare.EDIT)


@pytest.mark.unit
class TestPageCommentModel:
    @pytest.mark.django_db
    def test_comment_creation_and_thread(self, workspace, create_user):
        page = Page.objects.create(workspace=workspace, owned_by=create_user, name="Doc")
        root = PageComment.objects.create(page=page, workspace=workspace, actor=create_user, comment_html="<p>hi</p>")
        reply = PageComment.objects.create(
            page=page, workspace=workspace, actor=create_user, comment_html="<p>reply</p>", parent=root
        )
        assert reply.parent_id == root.id
        assert root.resolved is False


def _make_user(prefix):
    from uuid import uuid4

    from plane.db.models import User

    unique_id = uuid4().hex[:8]
    return User.objects.create(email=f"{prefix}-{unique_id}@plane.so", username=f"{prefix}_{unique_id}")
