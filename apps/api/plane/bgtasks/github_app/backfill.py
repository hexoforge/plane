# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from plane.db.models import (
    Account,
    GithubBackfillRun,
    GithubCommentLink,
    GithubIssueLink,
    Issue,
    IssueAssignee,
    IssueComment,
    IssueLabel,
    Label,
    ProjectMember,
)
from plane.utils.exception_logger import log_exception
from plane.utils.github_app.client import GithubAppClient
from plane.utils.github_app.refs import extract_closing_refs, extract_refs

from .handlers import apply_pull_request_link
from .sync import (
    body_hash,
    get_or_create_bot_user,
    get_state_mapping,
    move_issue_state,
    parse_gh_datetime,
    record_github_activity,
    render_markdown,
)


def match_or_create_labels(project, label_names):
    """Match GitHub label names to existing project Labels case-insensitively,
    creating any that don't already exist."""
    if not label_names:
        return []
    existing = {label.name.lower(): label for label in Label.objects.filter(project=project)}
    labels = []
    for name in dict.fromkeys(label_names):
        label = existing.get(name.lower())
        if not label:
            label = Label.objects.create(project=project, workspace=project.workspace, name=name, color="#60646C")
            existing[name.lower()] = label
        labels.append(label)
    return labels


def match_assignees(project, gh_assignees):
    """Match GitHub assignees to project members via their linked GitHub Account.
    Assignees with no linked, matching project member are skipped."""
    gh_ids = {str(assignee["id"]) for assignee in gh_assignees if assignee.get("id") is not None}
    if not gh_ids:
        return []
    member_ids = ProjectMember.objects.filter(project=project).values_list("member_id", flat=True)
    accounts = Account.objects.filter(provider="github", provider_account_id__in=gh_ids, user_id__in=member_ids)
    return [account.user for account in accounts]


def _import_comments(client, linked_repo, project, issue, issue_link, gh_issue_number, bot_user):
    for gh_comment in client.list_issue_comments(linked_repo.full_name, gh_issue_number):
        gh_comment_id = gh_comment.get("id")
        if GithubCommentLink.objects.filter(gh_comment_id=gh_comment_id).exists():
            continue
        body = gh_comment.get("body") or ""
        issue_comment = IssueComment.objects.create(
            project=project,
            issue=issue,
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


def _import_issue(client, run, linked_repo, project, gh_issue, bot_user, state_mapping):
    gh_issue_number = gh_issue.get("number")
    if GithubIssueLink.objects.filter(linked_repo=linked_repo, gh_issue_number=gh_issue_number).exists():
        return

    issue = Issue(
        project=project,
        workspace=project.workspace,
        name=gh_issue.get("title") or f"GitHub issue #{gh_issue_number}",
        description_html=render_markdown(gh_issue.get("body")),
        external_source="github",
        external_id=str(gh_issue.get("id")),
    )
    # Issue and its link must land together: a dangling issue without a link would
    # be re-imported as a duplicate on the next run (idempotency keys off the link).
    with transaction.atomic():
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
    for label in match_or_create_labels(project, label_names):
        IssueLabel.objects.get_or_create(
            issue=issue, label=label, defaults={"project": project, "workspace": project.workspace}
        )

    for user in match_assignees(project, gh_issue.get("assignees") or []):
        IssueAssignee.objects.get_or_create(
            issue=issue, assignee=user, defaults={"project": project, "workspace": project.workspace}
        )

    record_github_activity(
        issue, bot_user, "created", f"imported from GitHub issue {linked_repo.full_name}#{gh_issue_number}"
    )

    _import_comments(client, linked_repo, project, issue, issue_link, gh_issue_number, bot_user)

    if gh_issue.get("state") == "closed" and run.include_closed_issues:
        target_state = (state_mapping.issue_closed_state if state_mapping else None) or project.default_state
        move_issue_state(issue, target_state, bot_user)


def _resolve_pr_issues(project, pr, imported_issues_by_number):
    text = "\n".join(filter(None, [(pr.get("head") or {}).get("ref"), pr.get("title"), pr.get("body")]))
    issues = {}
    for _identifier, sequence_id in extract_refs(text, [project.identifier]):
        issue = Issue.objects.filter(project=project, sequence_id=sequence_id).first()
        if issue:
            issues[issue.id] = issue
    for gh_number in extract_closing_refs(text):
        issue = imported_issues_by_number.get(gh_number)
        if issue:
            issues[issue.id] = issue
    return list(issues.values())


def _link_pull_request(linked_repo, project, pr, imported_issues_by_number, bot_user, state_mapping):
    issues = _resolve_pr_issues(project, pr, imported_issues_by_number)
    if not issues:
        return False

    is_merged = bool(pr.get("merged_at"))
    is_draft = bool(pr.get("draft"))
    action = "closed" if pr.get("state") == "closed" else "opened"
    if action == "closed":
        new_state = "merged" if is_merged else "closed"
    elif is_draft:
        new_state = "draft"
    else:
        new_state = "open"
    updated_at = parse_gh_datetime(pr.get("updated_at")) or timezone.now()

    for issue in issues:
        apply_pull_request_link(
            issue, project, linked_repo, pr, new_state, action, is_draft, updated_at, bot_user, state_mapping
        )
    return True


def _run_backfill(run):
    linked_repo = run.linked_repo
    project = run.project
    client = GithubAppClient(linked_repo.installation.installation_id)
    bot_user = get_or_create_bot_user(run.workspace)
    state_mapping = get_state_mapping(project)

    issue_state = "all" if run.include_closed_issues else "open"
    all_issues = client.list_repo_issues(linked_repo.full_name, state=issue_state)
    gh_issues = [issue for issue in all_issues if "pull_request" not in issue]
    run.total_issues = len(gh_issues)
    run.save(update_fields=["total_issues", "updated_at"])

    for gh_issue in gh_issues:
        try:
            _import_issue(client, run, linked_repo, project, gh_issue, bot_user, state_mapping)
            run.imported_issues += 1
        except Exception as e:
            log_exception(e)
            run.skipped_issues += 1
        run.save(update_fields=["imported_issues", "skipped_issues", "updated_at"])

    imported_issues_by_number = {
        link.gh_issue_number: link.issue
        for link in GithubIssueLink.objects.filter(linked_repo=linked_repo).select_related("issue")
    }

    gh_pulls = client.list_repo_pulls(linked_repo.full_name, state="all")
    relevant_pulls = [pr for pr in gh_pulls if pr.get("state") == "open" or pr.get("merged_at")]
    run.total_pull_requests = len(relevant_pulls)
    run.save(update_fields=["total_pull_requests", "updated_at"])

    for pr in relevant_pulls:
        try:
            if _link_pull_request(linked_repo, project, pr, imported_issues_by_number, bot_user, state_mapping):
                run.linked_pull_requests += 1
        except Exception as e:
            log_exception(e)
        run.save(update_fields=["linked_pull_requests", "updated_at"])


@shared_task
def run_github_backfill(run_id):
    run = (
        GithubBackfillRun.objects.filter(pk=run_id)
        .select_related("linked_repo", "linked_repo__installation", "project", "workspace")
        .first()
    )
    if not run or run.status != "queued":
        return

    run.status = "running"
    run.started_at = timezone.now()
    run.save(update_fields=["status", "started_at", "updated_at"])

    try:
        _run_backfill(run)
        run.status = "completed"
    except Exception as e:
        log_exception(e)
        run.status = "failed"
        run.error = str(e)[:2000]
    finally:
        run.completed_at = timezone.now()
        run.save(update_fields=["status", "completed_at", "error", "updated_at"])
