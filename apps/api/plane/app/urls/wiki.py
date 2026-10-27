# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.urls import path

from plane.app.views import (
    PageCollectionViewSet,
    PageCommentViewSet,
    PageShareViewSet,
    WikiPageViewSet,
    WikiPagesDescriptionViewSet,
    WikiPageVersionEndpoint,
    WikiTreeEndpoint,
)

urlpatterns = [
    path(
        "workspaces/<str:slug>/wiki/collections/",
        PageCollectionViewSet.as_view({"get": "list", "post": "create"}),
        name="wiki-collections",
    ),
    path(
        "workspaces/<str:slug>/wiki/collections/<uuid:pk>/",
        PageCollectionViewSet.as_view({"get": "retrieve", "patch": "partial_update", "delete": "destroy"}),
        name="wiki-collections",
    ),
    path(
        "workspaces/<str:slug>/wiki/pages/",
        WikiPageViewSet.as_view({"get": "list", "post": "create"}),
        name="wiki-pages",
    ),
    path(
        "workspaces/<str:slug>/wiki/pages/<uuid:page_id>/",
        WikiPageViewSet.as_view({"get": "retrieve", "patch": "partial_update", "delete": "destroy"}),
        name="wiki-pages",
    ),
    path(
        "workspaces/<str:slug>/wiki/pages/<uuid:page_id>/archive/",
        WikiPageViewSet.as_view({"post": "archive", "delete": "unarchive"}),
        name="wiki-page-archive-unarchive",
    ),
    path(
        "workspaces/<str:slug>/wiki/pages/<uuid:page_id>/description/",
        WikiPagesDescriptionViewSet.as_view({"get": "retrieve", "patch": "partial_update"}),
        name="wiki-page-description",
    ),
    path(
        "workspaces/<str:slug>/wiki/pages/<uuid:page_id>/versions/",
        WikiPageVersionEndpoint.as_view(),
        name="wiki-page-versions",
    ),
    path(
        "workspaces/<str:slug>/wiki/pages/<uuid:page_id>/versions/<uuid:pk>/",
        WikiPageVersionEndpoint.as_view(),
        name="wiki-page-versions",
    ),
    path(
        "workspaces/<str:slug>/wiki/pages/<uuid:page_id>/shares/",
        PageShareViewSet.as_view({"get": "list", "post": "create"}),
        name="wiki-page-shares",
    ),
    path(
        "workspaces/<str:slug>/wiki/shares/<uuid:pk>/",
        PageShareViewSet.as_view({"patch": "partial_update", "delete": "destroy"}),
        name="wiki-shares",
    ),
    path(
        "workspaces/<str:slug>/wiki/pages/<uuid:page_id>/comments/",
        PageCommentViewSet.as_view({"get": "list", "post": "create"}),
        name="wiki-page-comments",
    ),
    path(
        "workspaces/<str:slug>/wiki/comments/<uuid:pk>/",
        PageCommentViewSet.as_view({"patch": "partial_update", "delete": "destroy"}),
        name="wiki-comments",
    ),
    path(
        "workspaces/<str:slug>/wiki/tree/",
        WikiTreeEndpoint.as_view(),
        name="wiki-tree",
    ),
]
