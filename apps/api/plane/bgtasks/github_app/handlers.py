# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.conf import settings
from django.utils import timezone

from plane.db.models import (
    GithubAppInstallation,
    GithubCommentLink,
    GithubIssueLink,
    GithubLinkedRepository,
    GithubPullRequestLink,
    Issue,
    IssueComment,
    IssueLabel,
    StateGroup,
)
from plane.utils.github_app.client import GithubAppClient
from plane.utils.github_app.refs import extract_refs

from .sync import (
    body_hash,
    ensure_bot_project_membership,
    get_linked_repo,
    get_or_create_bot_user,
    get_state_mapping,
    is_stale,
    match_labels,
    move_issue_state,
    parse_gh_datetime,
    record_github_activity,
    render_markdown,
    sync_issue_assignees,
)


def apply_pull_request_link(
    issue, project, linked_repo, pr, new_state, action, is_draft, updated_at, bot_user, state_mapping
):
    """Create or update a GithubPullRequestLink for one (issue, PR) pair and move
    the issue's state per the opened/merged mapping. Shared by the webhook handler
    and the backfill task so both honor the same never-move-backward-out-of-merged
    rule."""
    link = GithubPullRequestLink.objects.filter(issue=issue, pr_id=pr.get("id")).first()
    if link and is_stale(link.gh_updated_at, updated_at):
        return

    is_new = link is None
    previous_state = link.state if link else None
    # Never move a PR link backwards out of "merged".
    effective_state = "merged" if previous_state == "merged" else new_state

    if not link:
        link = GithubPullRequestLink(
            project=project,
            issue=issue,
            linked_repo=linked_repo,
            pr_id=pr.get("id"),
        )

    link.pr_number = pr.get("number")
    link.title = pr.get("title") or ""
    link.url = pr.get("html_url") or ""
    link.author_login = (pr.get("user") or {}).get("login", "")
    link.author_avatar_url = (pr.get("user") or {}).get("avatar_url")
    link.head_branch = (pr.get("head") or {}).get("ref", "")
    link.state = effective_state
    link.merged_at = parse_gh_datetime(pr.get("merged_at"))
    link.gh_updated_at = updated_at
    link.save()

    if is_new:
        record_github_activity(
            issue, bot_user, "created", f"linked pull request {linked_repo.full_name}#{link.pr_number}"
        )
    elif effective_state == "merged" and previous_state != "merged":
        record_github_activity(
            issue, bot_user, "updated", f"merged pull request {linked_repo.full_name}#{link.pr_number}"
        )

    if effective_state == "merged" and previous_state != "merged" and state_mapping:
        move_issue_state(issue, state_mapping.pr_merged_state, bot_user)
    elif (
        action in ("opened", "reopened", "ready_for_review")
        and not is_draft
        and previous_state != "merged"
        and state_mapping
    ):
        move_issue_state(issue, state_mapping.pr_opened_state, bot_user)


def handle_pull_request(payload):
    action = payload.get("action")
    pr = payload.get("pull_request") or {}
    repo = payload.get("repository") or {}
    installation = payload.get("installation") or {}

    linked_repo = get_linked_repo(installation.get("id"), repo.get("id"))
    if not linked_repo:
        return "skipped"

    project = linked_repo.project
    updated_at = parse_gh_datetime(pr.get("updated_at")) or timezone.now()
    text = "\n".join(filter(None, [(pr.get("head") or {}).get("ref"), pr.get("title"), pr.get("body")]))
    refs = extract_refs(text, [project.identifier])
    if not refs:
        return "skipped"

    is_merged = bool(pr.get("merged"))
    is_draft = bool(pr.get("draft"))
    if action == "closed":
        new_state = "merged" if is_merged else "closed"
    elif is_draft:
        new_state = "draft"
    else:
        new_state = "open"

    state_mapping = get_state_mapping(project)
    bot_user = get_or_create_bot_user(linked_repo.workspace)

    for _identifier, sequence_id in refs:
        issue = Issue.objects.filter(project=project, sequence_id=sequence_id).first()
        if not issue:
            continue
        apply_pull_request_link(
            issue, project, linked_repo, pr, new_state, action, is_draft, updated_at, bot_user, state_mapping
        )

    return "processed"


def _get_or_create_issue_link(linked_repo, gh_issue, bot_user, state_mapping):
    project = linked_repo.project
    gh_issue_number = gh_issue.get("number")
    issue_link = GithubIssueLink.objects.filter(linked_repo=linked_repo, gh_issue_number=gh_issue_number).first()
    if issue_link:
        return issue_link, False

    if state_mapping and not state_mapping.auto_create_issues:
        return None, False

    ensure_bot_project_membership(project, bot_user)

    issue = Issue(
        project=project,
        workspace=project.workspace,
        name=gh_issue.get("title") or f"GitHub issue #{gh_issue_number}",
        description_html=render_markdown(gh_issue.get("body")),
        external_source="github",
        external_id=str(gh_issue.get("id")),
    )
    issue.save(created_by_id=bot_user.id)

    issue_link = GithubIssueLink.objects.create(
        project=project,
        issue=issue,
        linked_repo=linked_repo,
        gh_issue_id=gh_issue.get("id"),
        gh_issue_number=gh_issue_number,
        url=gh_issue.get("html_url", ""),
        gh_state=gh_issue.get("state", "open"),
        gh_updated_at=parse_gh_datetime(gh_issue.get("updated_at")) or timezone.now(),
    )

    label_names = [label.get("name") for label in gh_issue.get("labels", []) if label.get("name")]
    for label in match_labels(project, label_names):
        IssueLabel.objects.get_or_create(
            issue=issue, label=label, defaults={"project": project, "workspace": project.workspace}
        )

    record_github_activity(
        issue, bot_user, "created", f"created from GitHub issue {linked_repo.full_name}#{gh_issue_number}"
    )
    return issue_link, True


def handle_issues(payload):
    action = payload.get("action")
    gh_issue = payload.get("issue") or {}
    repo = payload.get("repository") or {}
    installation = payload.get("installation") or {}

    # issue_comment-style "issues" events can also fire for pull requests;
    # GithubIssueLink only models native GitHub issues.
    if "pull_request" in gh_issue:
        return "skipped"

    linked_repo = get_linked_repo(installation.get("id"), repo.get("id"))
    if not linked_repo:
        return "skipped"

    project = linked_repo.project
    state_mapping = get_state_mapping(project)
    bot_user = get_or_create_bot_user(linked_repo.workspace)
    client = GithubAppClient(linked_repo.installation.installation_id)

    issue_link, created = _get_or_create_issue_link(linked_repo, gh_issue, bot_user, state_mapping)
    if not issue_link:
        return "skipped"

    updated_at = parse_gh_datetime(gh_issue.get("updated_at")) or timezone.now()
    if created:
        sync_issue_assignees(issue_link.issue, project, gh_issue.get("assignees") or [], issue_link, client=client)
        return "processed"

    if is_stale(issue_link.gh_updated_at, updated_at):
        return "skipped"

    issue = issue_link.issue
    sync_issue_assignees(issue, project, gh_issue.get("assignees") or [], issue_link, client=client)

    if action == "labeled":
        label_name = (payload.get("label") or {}).get("name")
        for label in match_labels(project, [label_name] if label_name else []):
            IssueLabel.objects.get_or_create(
                issue=issue, label=label, defaults={"project": project, "workspace": project.workspace}
            )
        return "processed"

    if action == "edited":
        issue.name = gh_issue.get("title") or issue.name
        issue.description_html = render_markdown(gh_issue.get("body"))
        issue.description_binary = None
        issue.save(
            update_fields=["name", "description_html", "description_stripped", "description_binary", "updated_at"]
        )

    elif action == "closed":
        # A Plane item already marked done shouldn't be yanked into whatever
        # state GitHub-closed is mapped to (which may be a "cancelled" state).
        already_done = issue.state and issue.state.group == StateGroup.COMPLETED
        if not already_done:
            target_state = (state_mapping.issue_closed_state if state_mapping else None) or project.default_state
            move_issue_state(issue, target_state, bot_user)

    elif action == "reopened":
        target_state = (state_mapping.issue_reopened_state if state_mapping else None) or project.default_state
        move_issue_state(issue, target_state, bot_user)

    issue_link.gh_state = gh_issue.get("state", issue_link.gh_state)
    issue_link.url = gh_issue.get("html_url", issue_link.url)
    issue_link.gh_updated_at = updated_at
    issue_link.save(update_fields=["gh_state", "url", "gh_updated_at", "updated_at"])

    return "processed"


def _is_own_app_comment(comment):
    """True if this comment was posted by our own GitHub App.

    The App only ever posts comments that originated from Plane, so any comment
    it authored is an echo. Detect it before a GithubCommentLink exists, closing
    the window where a fast webhook echo would otherwise be mirrored back as a
    duplicate Plane comment.
    """
    app = comment.get("performed_via_github_app") or {}
    app_id = settings.GITHUB_APP_ID
    if app_id and str(app.get("id")) == str(app_id):
        return True

    slug = settings.GITHUB_APP_SLUG
    user = comment.get("user") or {}
    return bool(slug) and user.get("type") == "Bot" and user.get("login") == f"{slug}[bot]"


def handle_issue_comment(payload):
    action = payload.get("action")
    gh_issue = payload.get("issue") or {}
    comment = payload.get("comment") or {}
    repo = payload.get("repository") or {}
    installation = payload.get("installation") or {}

    # Comments on pull requests arrive as issue_comment too; only native
    # GitHub issues map to a GithubIssueLink.
    if "pull_request" in gh_issue:
        return "skipped"

    # Drop echoes of comments we posted ourselves, even before their
    # GithubCommentLink(source="plane") row has been written.
    if _is_own_app_comment(comment):
        return "skipped"

    linked_repo = get_linked_repo(installation.get("id"), repo.get("id"))
    if not linked_repo:
        return "skipped"

    issue_link = GithubIssueLink.objects.filter(
        linked_repo=linked_repo, gh_issue_number=gh_issue.get("number")
    ).first()
    if not issue_link:
        return "skipped"

    gh_comment_id = comment.get("id")
    comment_link = GithubCommentLink.objects.filter(gh_comment_id=gh_comment_id).first()

    # A comment we posted to GitHub ourselves, echoed back by the webhook.
    if comment_link and comment_link.source == "plane":
        return "skipped"

    bot_user = get_or_create_bot_user(linked_repo.workspace)
    project = linked_repo.project
    body = comment.get("body") or ""

    if action == "created":
        if comment_link:
            return "skipped"
        issue_comment = IssueComment.objects.create(
            project=project,
            issue=issue_link.issue,
            actor=bot_user,
            comment_html=render_markdown(body),
            external_source="github",
            external_id=str(gh_comment_id),
        )
        GithubCommentLink.objects.create(
            workspace=project.workspace,
            issue_comment=issue_comment,
            issue_link=issue_link,
            gh_comment_id=gh_comment_id,
            source="github",
            last_synced_hash=body_hash(body),
        )
        record_github_activity(issue_link.issue, bot_user, "created", "added a comment via GitHub")
        return "processed"

    if action == "edited":
        if not comment_link:
            return "skipped"
        new_hash = body_hash(body)
        if new_hash == comment_link.last_synced_hash:
            return "skipped"
        issue_comment = comment_link.issue_comment
        issue_comment.comment_html = render_markdown(body)
        issue_comment.save()
        comment_link.last_synced_hash = new_hash
        comment_link.save(update_fields=["last_synced_hash", "updated_at"])
        return "processed"

    if action == "deleted":
        if not comment_link:
            return "skipped"
        comment_link.issue_comment.delete()
        comment_link.delete()
        return "processed"

    return "skipped"


def handle_installation(payload):
    action = payload.get("action")
    installation_payload = payload.get("installation") or {}
    installation = GithubAppInstallation.objects.filter(
        installation_id=installation_payload.get("id")
    ).first()
    if not installation:
        return "skipped"

    if action == "deleted":
        GithubLinkedRepository.objects.filter(installation=installation).update(is_active=False)
        installation.delete()
    elif action == "suspend":
        installation.suspended_at = timezone.now()
        installation.save(update_fields=["suspended_at", "updated_at"])
    elif action == "unsuspend":
        installation.suspended_at = None
        installation.save(update_fields=["suspended_at", "updated_at"])
    else:
        return "skipped"

    return "processed"


def handle_installation_repositories(payload):
    action = payload.get("action")
    if action != "removed":
        return "skipped"

    installation_payload = payload.get("installation") or {}
    installation_id = installation_payload.get("id")
    removed = payload.get("repositories_removed") or []
    repo_ids = [repo.get("id") for repo in removed if repo.get("id") is not None]
    if not repo_ids:
        return "skipped"

    GithubLinkedRepository.objects.filter(
        installation__installation_id=installation_id, repo_id__in=repo_ids
    ).update(is_active=False)
    return "processed"
