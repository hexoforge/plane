# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from rest_framework import status
from rest_framework.response import Response

from plane.app.permissions import ROLE, allow_permission
from plane.app.serializers import GithubIssueLinkSerializer, GithubPullRequestLinkSerializer
from plane.db.models import GithubIssueLink, GithubPullRequestLink, ProjectMember

from ..base import BaseAPIView


class GithubIssueDetailEndpoint(BaseAPIView):
    @allow_permission(allowed_roles=[ROLE.ADMIN, ROLE.MEMBER, ROLE.GUEST], level="PROJECT")
    def get(self, request, slug, project_id, issue_id):
        pr_links = GithubPullRequestLink.objects.filter(issue_id=issue_id, project_id=project_id).select_related(
            "linked_repo"
        )
        issue_link = (
            GithubIssueLink.objects.filter(issue_id=issue_id, project_id=project_id)
            .select_related("linked_repo")
            .first()
        )

        project_member = ProjectMember.objects.filter(
            workspace__slug=slug, project_id=project_id, member=request.user, is_active=True
        ).first()
        is_guest = bool(project_member) and project_member.role == ROLE.GUEST.value

        private_repo_present = any(link.linked_repo.private for link in pr_links) or (
            issue_link is not None and issue_link.linked_repo.private
        )
        if is_guest and private_repo_present:
            return Response(
                {"error": "You don't have the required permissions."}, status=status.HTTP_403_FORBIDDEN
            )

        return Response(
            {
                "pull_requests": GithubPullRequestLinkSerializer(pr_links, many=True).data,
                "issue_link": GithubIssueLinkSerializer(issue_link).data if issue_link else None,
            },
            status=status.HTTP_200_OK,
        )
