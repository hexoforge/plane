# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.db.models import Count, Q
from rest_framework import status
from rest_framework.response import Response

from plane.app.permissions import ROLE, WikiPagePermission
from plane.app.permissions.page import get_scope_role
from plane.app.serializers import PageCollectionSerializer
from plane.db.models import Page, PageCollection

from ..base import BaseAPIView


class WikiTreeEndpoint(BaseAPIView):
    """Company wiki collections with their (minimal) nested pages."""

    permission_classes = [WikiPagePermission]

    def get(self, request, slug):
        role = get_scope_role(request.user, slug, None)

        collections_qs = PageCollection.objects.filter(
            workspace__slug=slug, project__isnull=True, archived_at__isnull=True
        )
        if role != ROLE.ADMIN.value:
            collections_qs = collections_qs.filter(Q(access=PageCollection.PUBLIC_ACCESS) | Q(owned_by=request.user))
        collections = PageCollectionSerializer(
            collections_qs.annotate(
                page_count=Count("pages", filter=Q(pages__archived_at__isnull=True), distinct=True)
            ),
            many=True,
        ).data

        pages = (
            Page.objects.filter(workspace__slug=slug, is_global=True, archived_at__isnull=True)
            .filter(
                Q(owned_by=request.user)
                | Q(access=Page.PUBLIC_ACCESS)
                | Q(shares__user=request.user, shares__deleted_at__isnull=True)
            )
            .distinct()
            .values("id", "name", "parent", "collection", "access", "sort_order", "archived_at", "logo_props")
        )

        return Response({"collections": collections, "pages": list(pages)}, status=status.HTTP_200_OK)
