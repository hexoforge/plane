# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Python imports
import hashlib

# Third party imports
from celery import shared_task

# Django imports
from django.utils import timezone

# Module imports
from plane.db.models import (
    GithubCommentLink,
    GithubIssueLink,
    GithubProjectStateMapping,
    Issue,
    IssueComment,
    StateGroup,
    User,
)
from plane.utils.exception_logger import log_exception
from plane.utils.github_app.client import GithubAppClient

GITHUB_BOT_USERNAME_PREFIX = "github-bot-"
CLOSED_STATE_GROUPS = {StateGroup.COMPLETED, StateGroup.CANCELLED}
STATE_REASON_BY_GROUP = {StateGroup.COMPLETED: "completed", StateGroup.CANCELLED: "not_planned"}


def _hash_body(body):
    return hashlib.sha256((body or "").encode("utf-8")).hexdigest()


def _is_github_bot_actor(actor_id):
    if not actor_id:
        return False
    return User.objects.filter(
        id=actor_id, is_bot=True, username__startswith=GITHUB_BOT_USERNAME_PREFIX
    ).exists()


@shared_task
def sync_issue_state_to_github(issue_id, actor_id=None):
    """Close the linked GitHub issue when the work item enters a completed/cancelled
    state group, and reopen it when the work item leaves that group."""
    try:
        if _is_github_bot_actor(actor_id):
            return

        issue = Issue.objects.filter(pk=issue_id).select_related("state").first()
        if not issue or not issue.state:
            return

        link = (
            GithubIssueLink.objects.filter(issue_id=issue_id)
            .select_related("linked_repo", "linked_repo__installation")
            .first()
        )
        if not link:
            return

        group = issue.state.group
        desired_state = "closed" if group in CLOSED_STATE_GROUPS else "open"
        state_reason = STATE_REASON_BY_GROUP.get(group) if desired_state == "closed" else None

        client = GithubAppClient(link.linked_repo.installation.installation_id)
        response = client.update_issue_state(
            link.linked_repo.full_name, link.gh_issue_number, desired_state, state_reason
        )

        link.gh_state = response.get("state", desired_state)
        link.gh_updated_at = timezone.now()
        link.save(update_fields=["gh_state", "gh_updated_at"])
    except Exception as e:
        log_exception(e)


@shared_task
def sync_comment_to_github(comment_id, action):
    """Mirror a Plane comment create/update/delete to the linked GitHub issue.

    `action` is one of "create", "update", "delete". Uses GithubCommentLink(source="plane")
    to find the GitHub-side comment id and to record the body hash so the webhook echo
    (and no-op edits) can be skipped.
    """
    try:
        comment = IssueComment.all_objects.filter(pk=comment_id).select_related("issue").first()
        if not comment:
            return
        if comment.external_source == "github" or _is_github_bot_actor(comment.actor_id):
            return

        link = (
            GithubIssueLink.objects.filter(issue_id=comment.issue_id)
            .select_related("linked_repo", "linked_repo__installation")
            .first()
        )
        if not link:
            return

        mapping = GithubProjectStateMapping.objects.filter(project_id=comment.project_id).first()
        if mapping is not None and not mapping.sync_comments:
            return

        client = GithubAppClient(link.linked_repo.installation.installation_id)

        if action == "delete":
            # The comment's own soft-delete cascades to its GithubCommentLink (CASCADE FK),
            # so it may already be gone from the default manager by the time this runs.
            comment_link = GithubCommentLink.all_objects.filter(
                issue_comment_id=comment_id, source="plane"
            ).first()
            if not comment_link:
                return
            client.delete_issue_comment(link.linked_repo.full_name, comment_link.gh_comment_id)
            comment_link.delete()
            return

        comment_link = GithubCommentLink.objects.filter(issue_comment_id=comment_id, source="plane").first()

        body = comment.comment_stripped
        body_hash = _hash_body(body)

        if action == "create":
            if comment_link:
                return
            response = client.create_issue_comment(link.linked_repo.full_name, link.gh_issue_number, body)
            GithubCommentLink.objects.create(
                workspace_id=comment.workspace_id,
                issue_comment_id=comment.id,
                issue_link=link,
                gh_comment_id=response["id"],
                source="plane",
                last_synced_hash=body_hash,
            )
            return

        if action == "update":
            if not comment_link or comment_link.last_synced_hash == body_hash:
                return
            client.update_issue_comment(link.linked_repo.full_name, comment_link.gh_comment_id, body)
            comment_link.last_synced_hash = body_hash
            comment_link.save(update_fields=["last_synced_hash"])
    except Exception as e:
        log_exception(e)
