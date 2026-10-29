# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from rest_framework import serializers

from .base import DynamicBaseSerializer
from .state import StateLiteSerializer
from plane.db.models import (
    GithubBackfillRun,
    GithubIssueLink,
    GithubLinkedRepository,
    GithubProjectStateMapping,
    GithubPullRequestLink,
)


class GithubLinkedRepositorySerializer(DynamicBaseSerializer):
    class Meta:
        model = GithubLinkedRepository
        fields = [
            "id",
            "project_id",
            "workspace_id",
            "installation_id",
            "repo_id",
            "full_name",
            "private",
            "default_branch",
            "html_url",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "workspace_id", "created_at"]


class GithubProjectStateMappingSerializer(DynamicBaseSerializer):
    pr_opened_state_detail = StateLiteSerializer(source="pr_opened_state", read_only=True)
    pr_merged_state_detail = StateLiteSerializer(source="pr_merged_state", read_only=True)
    issue_closed_state_detail = StateLiteSerializer(source="issue_closed_state", read_only=True)
    issue_reopened_state_detail = StateLiteSerializer(source="issue_reopened_state", read_only=True)

    class Meta:
        model = GithubProjectStateMapping
        fields = [
            "id",
            "project_id",
            "pr_opened_state",
            "pr_merged_state",
            "issue_closed_state",
            "issue_reopened_state",
            "pr_opened_state_detail",
            "pr_merged_state_detail",
            "issue_closed_state_detail",
            "issue_reopened_state_detail",
            "auto_create_issues",
            "sync_comments",
            "sync_assignees",
        ]
        read_only_fields = ["id", "project_id"]


class GithubPullRequestLinkSerializer(DynamicBaseSerializer):
    repository_full_name = serializers.CharField(source="linked_repo.full_name", read_only=True)

    class Meta:
        model = GithubPullRequestLink
        fields = [
            "id",
            "issue_id",
            "linked_repo_id",
            "repository_full_name",
            "pr_number",
            "pr_id",
            "title",
            "url",
            "author_login",
            "author_avatar_url",
            "state",
            "head_branch",
            "merged_at",
            "gh_updated_at",
        ]
        read_only_fields = [f for f in fields if f != "repository_full_name"]


class GithubBackfillRunSerializer(DynamicBaseSerializer):
    class Meta:
        model = GithubBackfillRun
        fields = [
            "id",
            "project_id",
            "linked_repo_id",
            "status",
            "include_closed_issues",
            "started_at",
            "completed_at",
            "total_issues",
            "imported_issues",
            "skipped_issues",
            "total_pull_requests",
            "linked_pull_requests",
            "error",
            "created_at",
        ]
        read_only_fields = [f for f in fields if f not in ("include_closed_issues",)]


class GithubIssueLinkSerializer(DynamicBaseSerializer):
    repository_full_name = serializers.CharField(source="linked_repo.full_name", read_only=True)

    class Meta:
        model = GithubIssueLink
        fields = [
            "id",
            "issue_id",
            "linked_repo_id",
            "repository_full_name",
            "gh_issue_id",
            "gh_issue_number",
            "url",
            "gh_state",
            "gh_updated_at",
            "assignee_logins",
        ]
        read_only_fields = [f for f in fields if f != "repository_full_name"]
