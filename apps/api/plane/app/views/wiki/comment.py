# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from rest_framework import status
from rest_framework.response import Response

from plane.app.permissions import PageCommentPermission
from plane.app.serializers import PageCommentSerializer
from plane.db.models import PageComment, Workspace

from ..base import BaseViewSet


class PageCommentViewSet(BaseViewSet):
    """Page comments. Shared by the company wiki and the project wiki: list/create
    is nested under a page (.../pages/<page_id>/comments/), update/delete is flat
    (.../comments/<pk>/)."""

    serializer_class = PageCommentSerializer
    model = PageComment
    permission_classes = [PageCommentPermission]

    def get_queryset(self):
        qs = super().get_queryset().filter(workspace__slug=self.kwargs.get("slug"))
        page_id = self.kwargs.get("page_id")
        if page_id:
            qs = qs.filter(page_id=page_id)
        return qs.select_related("actor")

    def create(self, request, *args, **kwargs):
        slug = self.kwargs.get("slug")
        page_id = self.kwargs.get("page_id")
        workspace = Workspace.objects.get(slug=slug)

        serializer = PageCommentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(workspace_id=workspace.id, page_id=page_id, actor_id=request.user.id)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
