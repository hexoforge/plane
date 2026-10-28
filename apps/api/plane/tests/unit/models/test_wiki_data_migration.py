# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
Exercises the 0124 data migration functions directly against the real model
classes. pytest runs with --nomigrations (schema is built straight from the
current models), so the migration graph never replays; this test still
verifies the forward/reverse RunPython callables are correct and idempotent.
"""

import importlib

import pytest
from django.apps import apps

from plane.db.models import Page, PageCollection, Project, ProjectPage

migration = importlib.import_module("plane.db.migrations.0124_wiki_default_collections")


@pytest.mark.unit
class TestWikiDefaultCollectionsDataMigration:
    @pytest.mark.django_db
    def test_creates_workspace_default_collection(self, workspace):
        migration.create_default_collections_and_assign_pages(apps, None)

        collection = PageCollection.objects.get(workspace=workspace, project__isnull=True)
        assert collection.is_default is True
        assert collection.name == "General"
        assert collection.owned_by_id == workspace.owner_id

    @pytest.mark.django_db
    def test_creates_project_default_collection_and_assigns_pages(self, workspace, create_user):
        project = Project.objects.create(name="Proj A", identifier="PRJA", workspace=workspace)
        page = Page.objects.create(workspace=workspace, owned_by=create_user, name="Doc")
        ProjectPage.objects.create(workspace=workspace, project=project, page=page)

        migration.create_default_collections_and_assign_pages(apps, None)

        collection = PageCollection.objects.get(workspace=workspace, project=project)
        assert collection.is_default is True
        page.refresh_from_db()
        assert page.collection_id == collection.id

    @pytest.mark.django_db
    def test_skips_project_without_pages(self, workspace):
        Project.objects.create(name="Empty Project", identifier="EMPT", workspace=workspace)

        migration.create_default_collections_and_assign_pages(apps, None)

        assert not PageCollection.objects.filter(workspace=workspace, project__isnull=False).exists()

    @pytest.mark.django_db
    def test_forward_is_idempotent(self, workspace):
        migration.create_default_collections_and_assign_pages(apps, None)
        migration.create_default_collections_and_assign_pages(apps, None)

        assert PageCollection.objects.filter(workspace=workspace, project__isnull=True, is_default=True).count() == 1

    @pytest.mark.django_db
    def test_reverse_removes_defaults_and_nulls_pages(self, workspace, create_user):
        project = Project.objects.create(name="Proj A", identifier="PRJA", workspace=workspace)
        page = Page.objects.create(workspace=workspace, owned_by=create_user, name="Doc")
        ProjectPage.objects.create(workspace=workspace, project=project, page=page)

        migration.create_default_collections_and_assign_pages(apps, None)
        assert PageCollection.objects.filter(is_default=True).count() == 2

        migration.remove_default_collections(apps, None)

        assert PageCollection.objects.filter(is_default=True).count() == 0
        page.refresh_from_db()
        assert page.collection_id is None
        # the page itself is untouched, only its collection link is cleared
        assert Page.objects.filter(id=page.id).exists()
