# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.db.models import Count, Q
from rest_framework import status
from rest_framework.response import Response

from plane.app.permissions import ROLE, PageCollectionPermission
from plane.app.permissions.page import get_scope_role
from plane.app.serializers import PageCollectionSerializer
from plane.db.models import PageCollection, Workspace

from ..base import BaseViewSet


class PageCollectionViewSet(BaseViewSet):
    """Page collections. Shared by the company wiki (no project_id in the URL)
    and the project wiki (project_id present)."""

    serializer_class = PageCollectionSerializer
    model = PageCollection
    permission_classes = [PageCollectionPermission]
    search_fields = ["name"]

    def get_queryset(self):
        slug = self.kwargs.get("slug")
        project_id = self.kwargs.get("project_id")
        qs = super().get_queryset().filter(workspace__slug=slug, archived_at__isnull=True)
        qs = qs.filter(project_id=project_id) if project_id else qs.filter(project__isnull=True)

        role = get_scope_role(self.request.user, slug, project_id)
        if role != ROLE.ADMIN.value:
            qs = qs.filter(Q(access=PageCollection.PUBLIC_ACCESS) | Q(owned_by=self.request.user))

        return self.filter_queryset(
            qs.annotate(
                page_count=Count("pages", filter=Q(pages__archived_at__isnull=True), distinct=True)
            )
        )

    def create(self, request, *args, **kwargs):
        slug = self.kwargs.get("slug")
        project_id = self.kwargs.get("project_id")
        workspace = Workspace.objects.get(slug=slug)

        serializer = PageCollectionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(workspace_id=workspace.id, project_id=project_id, owned_by_id=request.user.id)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        collection = self.get_object()
        if collection.is_default:
            return Response(
                {"error": "The default collection cannot be deleted"}, status=status.HTTP_400_BAD_REQUEST
            )
        return super().destroy(request, *args, **kwargs)
