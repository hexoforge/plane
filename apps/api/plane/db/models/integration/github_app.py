# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Django imports
from django.db import models

# Module imports
from plane.db.models.base import BaseModel


class GithubAppInstallation(BaseModel):
    class AccountType(models.TextChoices):
        USER = "User", "User"
        ORGANIZATION = "Organization", "Organization"

    workspace = models.ForeignKey(
        "db.Workspace", on_delete=models.CASCADE, related_name="github_app_installations"
    )
    installation_id = models.BigIntegerField(unique=True)
    account_login = models.CharField(max_length=255)
    account_type = models.CharField(max_length=20, choices=AccountType.choices)
    target_id = models.BigIntegerField()
    suspended_at = models.DateTimeField(null=True, blank=True)
    installed_by = models.ForeignKey(
        "db.User", on_delete=models.SET_NULL, null=True, related_name="github_app_installations"
    )

    class Meta:
        verbose_name = "Github App Installation"
        verbose_name_plural = "Github App Installations"
        db_table = "github_app_installations"
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=["workspace"],
                condition=models.Q(deleted_at__isnull=True),
                name="github_app_installation_unique_workspace_when_deleted_at_null",
            )
        ]

    def __str__(self):
        return f"{self.account_login} <{self.workspace.slug}>"


class GithubLinkedRepository(BaseModel):
    workspace = models.ForeignKey(
        "db.Workspace", on_delete=models.CASCADE, related_name="github_linked_repositories"
    )
    project = models.ForeignKey(
        "db.Project", on_delete=models.CASCADE, related_name="github_linked_repositories"
    )
    installation = models.ForeignKey(
        "db.GithubAppInstallation", on_delete=models.CASCADE, related_name="linked_repositories"
    )
    repo_id = models.BigIntegerField()
    full_name = models.CharField(max_length=500)
    private = models.BooleanField(default=False)
    default_branch = models.CharField(max_length=255, null=True, blank=True)
    html_url = models.URLField(max_length=500, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Github Linked Repository"
        verbose_name_plural = "Github Linked Repositories"
        db_table = "github_linked_repositories"
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=["project", "repo_id"],
                condition=models.Q(deleted_at__isnull=True),
                name="github_linked_repository_unique_project_repo_when_deleted_at_null",
            ),
            models.UniqueConstraint(
                fields=["workspace", "repo_id"],
                condition=models.Q(deleted_at__isnull=True),
                name="github_linked_repository_unique_workspace_repo_when_deleted_at_null",
            ),
        ]

    def __str__(self):
        return f"{self.full_name} <{self.project.name}>"


class GithubProjectStateMapping(BaseModel):
    workspace = models.ForeignKey(
        "db.Workspace", on_delete=models.CASCADE, related_name="github_project_state_mappings"
    )
    project = models.ForeignKey(
        "db.Project", on_delete=models.CASCADE, related_name="github_state_mapping"
    )
    pr_opened_state = models.ForeignKey(
        "db.State", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    pr_merged_state = models.ForeignKey(
        "db.State", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    issue_closed_state = models.ForeignKey(
        "db.State", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    issue_reopened_state = models.ForeignKey(
        "db.State", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    auto_create_issues = models.BooleanField(default=True)
    sync_comments = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Github Project State Mapping"
        verbose_name_plural = "Github Project State Mappings"
        db_table = "github_project_state_mappings"
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=["project"],
                condition=models.Q(deleted_at__isnull=True),
                name="github_project_state_mapping_unique_project_when_deleted_at_null",
            )
        ]

    def __str__(self):
        return f"State mapping <{self.project.name}>"


class GithubPullRequestLink(BaseModel):
    class PRState(models.TextChoices):
        OPEN = "open", "Open"
        CLOSED = "closed", "Closed"
        MERGED = "merged", "Merged"
        DRAFT = "draft", "Draft"

    workspace = models.ForeignKey(
        "db.Workspace", on_delete=models.CASCADE, related_name="github_pull_request_links"
    )
    project = models.ForeignKey(
        "db.Project", on_delete=models.CASCADE, related_name="github_pull_request_links"
    )
    issue = models.ForeignKey(
        "db.Issue", on_delete=models.CASCADE, related_name="github_pull_request_links"
    )
    linked_repo = models.ForeignKey(
        "db.GithubLinkedRepository", on_delete=models.CASCADE, related_name="pull_request_links"
    )
    pr_number = models.IntegerField()
    pr_id = models.BigIntegerField()
    title = models.TextField()
    url = models.URLField(max_length=500)
    author_login = models.CharField(max_length=255, null=True, blank=True)
    author_avatar_url = models.URLField(max_length=500, null=True, blank=True)
    state = models.CharField(max_length=20, choices=PRState.choices)
    head_branch = models.CharField(max_length=500, null=True, blank=True)
    merged_at = models.DateTimeField(null=True, blank=True)
    gh_updated_at = models.DateTimeField()

    class Meta:
        verbose_name = "Github Pull Request Link"
        verbose_name_plural = "Github Pull Request Links"
        db_table = "github_pull_request_links"
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=["issue", "pr_id"],
                condition=models.Q(deleted_at__isnull=True),
                name="github_pr_link_unique_issue_pr_when_deleted_at_null",
            )
        ]

    def __str__(self):
        return f"{self.linked_repo.full_name}#{self.pr_number}"


class GithubIssueLink(BaseModel):
    workspace = models.ForeignKey(
        "db.Workspace", on_delete=models.CASCADE, related_name="github_issue_links"
    )
    project = models.ForeignKey(
        "db.Project", on_delete=models.CASCADE, related_name="github_issue_links"
    )
    issue = models.OneToOneField(
        "db.Issue", on_delete=models.CASCADE, related_name="github_issue_link", null=True, blank=True
    )
    linked_repo = models.ForeignKey(
        "db.GithubLinkedRepository", on_delete=models.CASCADE, related_name="issue_links"
    )
    gh_issue_id = models.BigIntegerField()
    gh_issue_number = models.IntegerField()
    url = models.URLField(max_length=500)
    gh_state = models.CharField(max_length=20)
    gh_updated_at = models.DateTimeField()

    class Meta:
        verbose_name = "Github Issue Link"
        verbose_name_plural = "Github Issue Links"
        db_table = "github_issue_links"
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=["issue"],
                condition=models.Q(deleted_at__isnull=True),
                name="github_issue_link_unique_issue_when_deleted_at_null",
            ),
            models.UniqueConstraint(
                fields=["linked_repo", "gh_issue_number"],
                name="github_issue_link_unique_linked_repo_gh_issue_number",
            ),
        ]

    def __str__(self):
        return f"{self.linked_repo.full_name}#{self.gh_issue_number}"


class GithubCommentLink(BaseModel):
    class Source(models.TextChoices):
        GITHUB = "github", "Github"
        PLANE = "plane", "Plane"

    workspace = models.ForeignKey(
        "db.Workspace", on_delete=models.CASCADE, related_name="github_comment_links"
    )
    issue_comment = models.ForeignKey(
        "db.IssueComment", on_delete=models.CASCADE, related_name="github_comment_links"
    )
    issue_link = models.ForeignKey(
        "db.GithubIssueLink", on_delete=models.CASCADE, related_name="comment_links"
    )
    gh_comment_id = models.BigIntegerField(unique=True)
    source = models.CharField(max_length=10, choices=Source.choices)
    last_synced_hash = models.CharField(max_length=64, null=True, blank=True)

    class Meta:
        verbose_name = "Github Comment Link"
        verbose_name_plural = "Github Comment Links"
        db_table = "github_comment_links"
        ordering = ("-created_at",)

    def __str__(self):
        return f"comment<{self.gh_comment_id}>"


class GithubWebhookDelivery(BaseModel):
    class Status(models.TextChoices):
        RECEIVED = "received", "Received"
        PROCESSED = "processed", "Processed"
        FAILED = "failed", "Failed"
        SKIPPED = "skipped", "Skipped"

    delivery_id = models.CharField(max_length=255, unique=True)
    event = models.CharField(max_length=100)
    action = models.CharField(max_length=100, null=True, blank=True)
    installation_id = models.BigIntegerField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RECEIVED)
    error = models.TextField(null=True, blank=True)
    received_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    payload = models.JSONField(default=dict)

    class Meta:
        verbose_name = "Github Webhook Delivery"
        verbose_name_plural = "Github Webhook Deliveries"
        db_table = "github_webhook_deliveries"
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.event} <{self.delivery_id}>"
