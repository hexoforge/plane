# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Django imports
from django.db import models
from django.db.models import Q

# Module imports
from plane.db.models.base import BaseModel
from plane.db.models.project import ProjectBaseModel


class GithubAppInstallation(BaseModel):
    ACCOUNT_TYPE_CHOICES = (("User", "User"), ("Organization", "Organization"))

    workspace = models.ForeignKey(
        "db.Workspace", on_delete=models.CASCADE, related_name="github_app_installations"
    )
    installation_id = models.BigIntegerField(unique=True)
    account_login = models.CharField(max_length=255)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPE_CHOICES)
    target_id = models.BigIntegerField()
    suspended_at = models.DateTimeField(null=True, blank=True)
    installed_by = models.ForeignKey(
        "db.User", on_delete=models.SET_NULL, null=True, related_name="github_app_installations"
    )

    def __str__(self):
        return f"{self.account_login} <{self.workspace.slug}>"

    class Meta:
        verbose_name = "Github App Installation"
        verbose_name_plural = "Github App Installations"
        db_table = "github_app_installations"
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=["workspace"],
                condition=Q(deleted_at__isnull=True),
                name="github_app_installation_unique_workspace_when_deleted_at_null",
            )
        ]


class GithubLinkedRepository(ProjectBaseModel):
    installation = models.ForeignKey(
        "db.GithubAppInstallation", on_delete=models.CASCADE, related_name="linked_repositories"
    )
    repo_id = models.BigIntegerField()
    full_name = models.CharField(max_length=500)
    private = models.BooleanField(default=False)
    default_branch = models.CharField(max_length=255, default="main")
    html_url = models.URLField(max_length=1000)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.full_name} <{self.project.identifier}>"

    class Meta:
        verbose_name = "Github Linked Repository"
        verbose_name_plural = "Github Linked Repositories"
        db_table = "github_linked_repositories"
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=["project", "repo_id"],
                condition=Q(deleted_at__isnull=True),
                name="github_linked_repo_unique_project_repo_when_deleted_at_null",
            ),
            models.UniqueConstraint(
                fields=["workspace", "repo_id"],
                condition=Q(deleted_at__isnull=True),
                name="github_linked_repo_unique_workspace_repo_when_deleted_at_null",
            ),
        ]


class GithubProjectStateMapping(ProjectBaseModel):
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

    def __str__(self):
        return f"State mapping <{self.project.identifier}>"

    class Meta:
        verbose_name = "Github Project State Mapping"
        verbose_name_plural = "Github Project State Mappings"
        db_table = "github_project_state_mappings"
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=["project"],
                condition=Q(deleted_at__isnull=True),
                name="github_state_mapping_unique_project_when_deleted_at_null",
            )
        ]


class GithubPullRequestLink(ProjectBaseModel):
    STATE_CHOICES = (
        ("open", "Open"),
        ("closed", "Closed"),
        ("merged", "Merged"),
        ("draft", "Draft"),
    )

    issue = models.ForeignKey("db.Issue", on_delete=models.CASCADE, related_name="github_pull_request_links")
    linked_repo = models.ForeignKey(
        "db.GithubLinkedRepository", on_delete=models.CASCADE, related_name="pull_request_links"
    )
    pr_number = models.IntegerField()
    pr_id = models.BigIntegerField()
    title = models.TextField()
    url = models.URLField(max_length=1000)
    author_login = models.CharField(max_length=255, blank=True)
    author_avatar_url = models.URLField(max_length=1000, blank=True, null=True)
    state = models.CharField(max_length=20, choices=STATE_CHOICES)
    head_branch = models.CharField(max_length=500, blank=True)
    merged_at = models.DateTimeField(null=True, blank=True)
    gh_updated_at = models.DateTimeField()

    def __str__(self):
        return f"{self.linked_repo.full_name}#{self.pr_number}"

    class Meta:
        verbose_name = "Github Pull Request Link"
        verbose_name_plural = "Github Pull Request Links"
        db_table = "github_pull_request_links"
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=["issue", "pr_id"],
                condition=Q(deleted_at__isnull=True),
                name="github_pr_link_unique_issue_pr_when_deleted_at_null",
            )
        ]


class GithubIssueLink(ProjectBaseModel):
    issue = models.OneToOneField("db.Issue", on_delete=models.CASCADE, related_name="github_issue_link")
    linked_repo = models.ForeignKey(
        "db.GithubLinkedRepository", on_delete=models.CASCADE, related_name="issue_links"
    )
    gh_issue_id = models.BigIntegerField()
    gh_issue_number = models.IntegerField()
    url = models.URLField(max_length=1000)
    gh_state = models.CharField(max_length=20)
    gh_updated_at = models.DateTimeField()

    def __str__(self):
        return f"{self.linked_repo.full_name}#{self.gh_issue_number}"

    class Meta:
        verbose_name = "Github Issue Link"
        verbose_name_plural = "Github Issue Links"
        db_table = "github_issue_links"
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=["linked_repo", "gh_issue_number"],
                condition=Q(deleted_at__isnull=True),
                name="github_issue_link_unique_repo_number_when_deleted_at_null",
            ),
            models.UniqueConstraint(
                fields=["issue"],
                condition=Q(deleted_at__isnull=True),
                name="github_issue_link_unique_issue_when_deleted_at_null",
            ),
        ]


class GithubCommentLink(BaseModel):
    SOURCE_CHOICES = (("github", "Github"), ("plane", "Plane"))

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
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES)
    last_synced_hash = models.CharField(max_length=64, blank=True)

    def __str__(self):
        return f"comment <{self.gh_comment_id}>"

    class Meta:
        verbose_name = "Github Comment Link"
        verbose_name_plural = "Github Comment Links"
        db_table = "github_comment_links"
        ordering = ("-created_at",)


class GithubWebhookDelivery(BaseModel):
    STATUS_CHOICES = (
        ("received", "Received"),
        ("processed", "Processed"),
        ("failed", "Failed"),
        ("skipped", "Skipped"),
    )

    delivery_id = models.CharField(max_length=255, unique=True)
    event = models.CharField(max_length=100)
    action = models.CharField(max_length=100, blank=True, null=True)
    installation_id = models.BigIntegerField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="received")
    error = models.TextField(blank=True)
    received_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    payload = models.JSONField(default=dict)

    def __str__(self):
        return f"{self.event} <{self.delivery_id}>"

    class Meta:
        verbose_name = "Github Webhook Delivery"
        verbose_name_plural = "Github Webhook Deliveries"
        db_table = "github_webhook_deliveries"
        ordering = ("-received_at",)
