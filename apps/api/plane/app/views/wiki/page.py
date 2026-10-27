# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Python imports
import json
from datetime import datetime
from django.core.serializers.json import DjangoJSONEncoder

# Django imports
from django.db.models import Q
from django.http import StreamingHttpResponse

# Third party imports
from rest_framework import status
from rest_framework.response import Response

# Module imports
from plane.app.permissions import WikiPagePermission
from plane.app.serializers import (
    WikiPageSerializer,
    WikiPageDetailSerializer,
    PageBinaryUpdateSerializer,
    PageVersionSerializer,
    PageVersionDetailSerializer,
)
from plane.db.models import Page, PageVersion, Workspace
from plane.utils.error_codes import ERROR_CODES

from ..base import BaseAPIView, BaseViewSet
from ..page.base import unarchive_archive_page_and_descendants
from plane.bgtasks.page_transaction_task import page_transaction
from plane.bgtasks.page_version_task import track_page_version


class WikiPageViewSet(BaseViewSet):
    """Company wiki pages: workspace scoped, is_global=True, no project."""

    serializer_class = WikiPageSerializer
    model = Page
    permission_classes = [WikiPagePermission]
    search_fields = ["name", "description_stripped"]

    def get_queryset(self):
        slug = self.kwargs.get("slug")
        qs = (
            super()
            .get_queryset()
            .filter(workspace__slug=slug, is_global=True)
            .filter(
                Q(owned_by=self.request.user)
                | Q(access=Page.PUBLIC_ACCESS)
                | Q(shares__user=self.request.user, shares__deleted_at__isnull=True)
            )
            .distinct()
        )

        collection_id = self.request.GET.get("collection")
        if collection_id:
            qs = qs.filter(collection_id=collection_id)

        parent_id = self.request.GET.get("parent")
        qs = qs.filter(parent_id=parent_id) if parent_id else qs.filter(parent__isnull=True)

        archived = self.request.GET.get("archived")
        if archived is not None:
            qs = qs.filter(archived_at__isnull=archived.lower() != "true")
        else:
            qs = qs.filter(archived_at__isnull=True)

        return self.filter_queryset(
            qs.select_related("owned_by", "collection").order_by("sort_order", "-created_at")
        )

    def list(self, request, slug):
        pages = WikiPageSerializer(self.get_queryset(), many=True).data
        return Response(pages, status=status.HTTP_200_OK)

    def create(self, request, slug):
        workspace = Workspace.objects.get(slug=slug)
        serializer = WikiPageSerializer(
            data=request.data,
            context={
                "workspace_id": workspace.id,
                "owned_by_id": request.user.id,
                "description_json": request.data.get("description_json", {}),
                "description_binary": request.data.get("description_binary", None),
                "description_html": request.data.get("description_html", "<p></p>"),
            },
        )
        if serializer.is_valid():
            serializer.save()
            page_transaction.delay(
                new_description_html=request.data.get("description_html", "<p></p>"),
                old_description_html=None,
                page_id=serializer.data["id"],
            )
            page = self.get_queryset().get(pk=serializer.data["id"])
            return Response(WikiPageDetailSerializer(page).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, slug, page_id):
        page = self.get_queryset().filter(pk=page_id).first()
        if page is None:
            return Response({"error": "Page not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(WikiPageDetailSerializer(page).data, status=status.HTTP_200_OK)

    def partial_update(self, request, slug, page_id):
        page = Page.objects.get(pk=page_id, workspace__slug=slug, is_global=True)

        if page.is_locked:
            return Response({"error": "Page is locked"}, status=status.HTTP_400_BAD_REQUEST)

        if page.access != request.data.get("access", page.access) and page.owned_by_id != request.user.id:
            return Response(
                {"error": "Access cannot be updated since this page is owned by someone else"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        old_description_html = page.description_html
        serializer = WikiPageDetailSerializer(page, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            if request.data.get("description_html"):
                page_transaction.delay(
                    new_description_html=request.data.get("description_html", "<p></p>"),
                    old_description_html=old_description_html,
                    page_id=page_id,
                )
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, slug, page_id):
        page = Page.objects.get(pk=page_id, workspace__slug=slug, is_global=True)
        if page.archived_at is None:
            return Response(
                {"error": "The page should be archived before deleting"}, status=status.HTTP_400_BAD_REQUEST
            )
        page.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def archive(self, request, slug, page_id):
        Page.objects.get(pk=page_id, workspace__slug=slug, is_global=True)
        unarchive_archive_page_and_descendants(page_id, datetime.now())
        return Response({"archived_at": str(datetime.now())}, status=status.HTTP_200_OK)

    def unarchive(self, request, slug, page_id):
        page = Page.objects.get(pk=page_id, workspace__slug=slug, is_global=True)
        if page.parent_id and page.parent.archived_at:
            page.parent = None
            page.save(update_fields=["parent"])
        unarchive_archive_page_and_descendants(page_id, None)
        return Response(status=status.HTTP_204_NO_CONTENT)


class WikiPagesDescriptionViewSet(BaseViewSet):
    permission_classes = [WikiPagePermission]

    def retrieve(self, request, slug, page_id):
        page = (
            Page.objects.filter(
                Q(owned_by=self.request.user)
                | Q(access=Page.PUBLIC_ACCESS)
                | Q(shares__user=self.request.user, shares__deleted_at__isnull=True),
                pk=page_id,
                workspace__slug=slug,
                is_global=True,
            )
            .distinct()
            .first()
        )
        if page is None:
            return Response({"error": "Page not found"}, status=status.HTTP_404_NOT_FOUND)
        binary_data = page.description_binary

        def stream_data():
            yield binary_data if binary_data else b""

        response = StreamingHttpResponse(stream_data(), content_type="application/octet-stream")
        response["Content-Disposition"] = 'attachment; filename="page_description.bin"'
        return response

    def partial_update(self, request, slug, page_id):
        page = (
            Page.objects.filter(
                Q(owned_by=self.request.user)
                | Q(access=Page.PUBLIC_ACCESS)
                | Q(shares__user=self.request.user, shares__deleted_at__isnull=True),
                pk=page_id,
                workspace__slug=slug,
                is_global=True,
            )
            .distinct()
            .first()
        )
        if page is None:
            return Response({"error": "Page not found"}, status=status.HTTP_404_NOT_FOUND)

        if page.is_locked:
            return Response(
                {"error_code": ERROR_CODES["PAGE_LOCKED"], "error_message": "PAGE_LOCKED"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if page.archived_at:
            return Response(
                {"error_code": ERROR_CODES["PAGE_ARCHIVED"], "error_message": "PAGE_ARCHIVED"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        old_description_html = page.description_html
        existing_instance = json.dumps({"description_html": old_description_html}, cls=DjangoJSONEncoder)

        serializer = PageBinaryUpdateSerializer(page, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            if request.data.get("description_html"):
                page_transaction.delay(
                    new_description_html=request.data.get("description_html", "<p></p>"),
                    old_description_html=old_description_html,
                    page_id=page_id,
                )
            track_page_version.delay(page_id=page_id, existing_instance=existing_instance, user_id=request.user.id)
            return Response({"message": "Updated successfully"})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class WikiPageVersionEndpoint(BaseAPIView):
    permission_classes = [WikiPagePermission]

    def get(self, request, slug, page_id, pk=None):
        if pk:
            page_version = (
                PageVersion.objects.filter(workspace__slug=slug, page__is_global=True, page_id=page_id, pk=pk)
                .distinct()
                .get()
            )
            serializer = PageVersionDetailSerializer(page_version)
            return Response(serializer.data, status=status.HTTP_200_OK)

        page_versions = PageVersion.objects.filter(workspace__slug=slug, page__is_global=True, page_id=page_id)
        serializer = PageVersionSerializer(page_versions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
