# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from plane.db.models import ProjectMember, WorkspaceMember, Page, PageCollection, PageShare
from plane.app.permissions import ROLE


from rest_framework.permissions import BasePermission, SAFE_METHODS


# Permission Mappings for workspace members
ADMIN = ROLE.ADMIN.value
MEMBER = ROLE.MEMBER.value
GUEST = ROLE.GUEST.value


def _check_role_action_access(request, role):
    """Map an HTTP method to the roles allowed to perform it."""
    method = request.method

    if method == "POST":
        return role in [ADMIN, MEMBER]

    if method in SAFE_METHODS:
        return role in [ADMIN, MEMBER, GUEST]

    if method in ["PUT", "PATCH"]:
        return role in [ADMIN, MEMBER]

    if method == "DELETE":
        return role == ADMIN

    return False


def _has_share_access(request, share):
    """A PageShare grants read access to any role; only EDIT grants write access."""
    if share is None:
        return False
    if request.method in SAFE_METHODS:
        return True
    if request.method in ["PUT", "PATCH"]:
        return share.role == PageShare.EDIT
    return False


def _get_workspace_role(user, slug):
    return (
        WorkspaceMember.objects.filter(member=user, workspace__slug=slug, is_active=True)
        .values_list("role", flat=True)
        .first()
    )


def get_scope_role(user, slug, project_id):
    """Resolve the requester's role for a wiki scope: project wiki when
    project_id is set, company wiki (workspace scoped) otherwise."""
    if project_id:
        return (
            ProjectMember.objects.filter(member=user, workspace__slug=slug, project_id=project_id, is_active=True)
            .values_list("role", flat=True)
            .first()
        )
    return _get_workspace_role(user, slug)


class ProjectPagePermission(BasePermission):
    """
    Custom permission to control access to pages within a workspace
    based on user roles, page visibility (public/private), and feature flags.
    """

    def has_permission(self, request, view):
        """
        Check basic project-level permissions before checking object-level permissions.
        """
        if request.user.is_anonymous:
            return False

        user_id = request.user.id
        slug = view.kwargs.get("slug")
        page_id = view.kwargs.get("page_id")
        project_id = view.kwargs.get("project_id")

        # Hook for extended validation
        extended_access, role = self._check_access_and_get_role(request, slug, project_id)
        if extended_access is False:
            return False

        if page_id:
            # Scope the page to the project in the URL. Resolving the page by
            # workspace + page_id alone allowed a member of one project to read
            # pages belonging to another project in the same workspace
            # (GHSA-g49r / GHSA-ghcr). Require an *active* ProjectPage link (both
            # conditions on the same relation so they match one row) so a page
            # removed from the project (soft-deleted link) is also denied.
            page = Page.objects.filter(
                id=page_id,
                workspace__slug=slug,
                project_pages__project_id=project_id,
                project_pages__deleted_at__isnull=True,
            ).first()
            if page is None:
                return False

            # Allow access if the user is the owner of the page
            if page.owned_by_id == user_id:
                return True

            # Handle private page access
            if page.access == Page.PRIVATE_ACCESS:
                return self._has_private_page_action_access(request, slug, page, project_id)

        # Handle public page access
        return self._has_public_page_action_access(request, role)

    def _check_project_member_access(self, request, slug, project_id):
        """
        Check if the user is a project member.
        """
        return (
            ProjectMember.objects.filter(
                member=request.user,
                workspace__slug=slug,
                is_active=True,
                project_id=project_id,
            )
            .values_list("role", flat=True)
            .first()
        )

    def _check_access_and_get_role(self, request, slug, project_id):
        """
        Hook for extended access checking
        Returns: True (allow), False (deny), None (continue with normal flow)
        """
        role = self._check_project_member_access(request, slug, project_id)
        if not role:
            return False, None
        return True, role

    def _has_private_page_action_access(self, request, slug, page, project_id):
        """
        Check access to private pages: the owner is handled earlier, so this only
        covers users the page has been explicitly shared with (PageShare).
        """
        share = PageShare.objects.filter(page=page, user=request.user, deleted_at__isnull=True).first()
        return _has_share_access(request, share)

    def _check_project_action_access(self, request, role):
        return _check_role_action_access(request, role)

    def _has_public_page_action_access(self, request, role):
        """
        Check if the user has permission to access a public page
        and can perform operations on the page.
        """
        project_member_exists = self._check_project_action_access(request, role)
        if not project_member_exists:
            return False
        return True


class WikiPagePermission(BasePermission):
    """
    Permission for company wiki pages: workspace scoped (is_global=True, no
    project). Guests are excluded entirely, unlike project pages.
    """

    def has_permission(self, request, view):
        if request.user.is_anonymous:
            return False

        slug = view.kwargs.get("slug")
        page_id = view.kwargs.get("page_id")

        role = _get_workspace_role(request.user, slug)
        if not role or role == GUEST:
            return False

        if page_id:
            page = Page.objects.filter(id=page_id, workspace__slug=slug, is_global=True).first()
            if page is None:
                return False

            if page.owned_by_id == request.user.id:
                return True

            if page.access == Page.PRIVATE_ACCESS:
                share = PageShare.objects.filter(page=page, user=request.user, deleted_at__isnull=True).first()
                return _has_share_access(request, share)

        return _check_role_action_access(request, role)


class PageCollectionPermission(BasePermission):
    """
    Permission for page collections. Used for both the company wiki
    (project_id absent) and project wiki (project_id present) collections.
    """

    def _get_role(self, request, view):
        return get_scope_role(request.user, view.kwargs.get("slug"), view.kwargs.get("project_id"))

    def has_permission(self, request, view):
        if request.user.is_anonymous:
            return False

        role = self._get_role(request, view)
        if not role or role == GUEST:
            return False

        if request.method == "POST":
            access = int(request.data.get("access", PageCollection.PUBLIC_ACCESS))
            if access == PageCollection.PRIVATE_ACCESS:
                return role == ADMIN
            return role in [ADMIN, MEMBER]

        # Visibility/ownership for retrieve, update and delete is enforced in
        # has_object_permission.
        return True

    def has_object_permission(self, request, view, obj):
        role = self._get_role(request, view)
        if not role or role == GUEST:
            return False

        if request.method in SAFE_METHODS:
            if obj.access == PageCollection.PUBLIC_ACCESS:
                return True
            return obj.owned_by_id == request.user.id or role == ADMIN

        # PATCH / DELETE: owner or admin manage any collection. Deleting the
        # default collection is additionally blocked in the view.
        return obj.owned_by_id == request.user.id or role == ADMIN


class PageSharePermission(BasePermission):
    """Only the page owner can view or manage its shares (design: 'only owner
    can share/delete/change access')."""

    def _resolve_role(self, request, view):
        return get_scope_role(request.user, view.kwargs.get("slug"), view.kwargs.get("project_id"))

    def has_permission(self, request, view):
        if request.user.is_anonymous:
            return False

        role = self._resolve_role(request, view)
        if not role or role == GUEST:
            return False

        slug = view.kwargs.get("slug")
        project_id = view.kwargs.get("project_id")
        page_id = view.kwargs.get("page_id")
        if page_id:
            if project_id:
                page = Page.objects.filter(
                    id=page_id,
                    workspace__slug=slug,
                    project_pages__project_id=project_id,
                    project_pages__deleted_at__isnull=True,
                ).first()
            else:
                page = Page.objects.filter(id=page_id, workspace__slug=slug, is_global=True).first()
            if page is None:
                return False
            return page.owned_by_id == request.user.id

        # shares/<sid>/ detail routes: defer to has_object_permission
        return True

    def has_object_permission(self, request, view, obj):
        role = self._resolve_role(request, view)
        if not role or role == GUEST:
            return False
        return obj.page.owned_by_id == request.user.id


class PageCommentPermission(BasePermission):
    """
    Anyone with read access to the page can read/post comments; a view-only
    share cannot comment. Editing or deleting a comment is limited to its
    author or an admin.
    """

    def _resolve_role_and_page(self, request, view):
        slug = view.kwargs.get("slug")
        project_id = view.kwargs.get("project_id")
        page_id = view.kwargs.get("page_id")

        role = get_scope_role(request.user, slug, project_id)
        if project_id:
            page = Page.objects.filter(
                id=page_id,
                workspace__slug=slug,
                project_pages__project_id=project_id,
                project_pages__deleted_at__isnull=True,
            ).first()
        else:
            page = Page.objects.filter(id=page_id, workspace__slug=slug, is_global=True).first()
        return role, page

    def has_permission(self, request, view):
        if request.user.is_anonymous:
            return False

        role, page = self._resolve_role_and_page(request, view)
        if not role or role == GUEST or page is None:
            return False

        if page.owned_by_id == request.user.id:
            return True

        if page.access == Page.PRIVATE_ACCESS:
            share = PageShare.objects.filter(page=page, user=request.user, deleted_at__isnull=True).first()
            if share is None:
                return False
            if request.method in SAFE_METHODS:
                return True
            # A view-only share may read comments but not post them.
            return share.role in [PageShare.COMMENT, PageShare.EDIT]

        return _check_role_action_access(request, role)

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        role, _ = self._resolve_role_and_page(request, view)
        return obj.actor_id == request.user.id or role == ADMIN
