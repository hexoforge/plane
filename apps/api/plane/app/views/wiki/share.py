# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from rest_framework import status
from rest_framework.response import Response

from plane.app.permissions import PageSharePermission
from plane.app.serializers import PageShareSerializer
from plane.db.models import PageShare, Workspace

from ..base import BaseViewSet


class PageShareViewSet(BaseViewSet):
    """Page shares. Shared by the company wiki and the project wiki: list/create
    is nested under a page (.../pages/<page_id>/shares/), update/delete is flat
    (.../shares/<pk>/)."""

    serializer_class = PageShareSerializer
    model = PageShare
    permission_classes = [PageSharePermission]

    def get_queryset(self):
        qs = super().get_queryset().filter(workspace__slug=self.kwargs.get("slug"))
        page_id = self.kwargs.get("page_id")
        if page_id:
            qs = qs.filter(page_id=page_id)
        return qs.select_related("user")

    def create(self, request, *args, **kwargs):
        slug = self.kwargs.get("slug")
        page_id = self.kwargs.get("page_id")
        workspace = Workspace.objects.get(slug=slug)

        serializer = PageShareSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(workspace_id=workspace.id, page_id=page_id)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
