# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import hashlib
import uuid
from urllib.parse import urlparse

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from plane.db.models import (
    GithubAppInstallation,
    GithubLinkedRepository,
    GithubProjectStateMapping,
    IssueActivity,
    IssueAssignee,
    ProjectMember,
    User,
    WorkspaceMember,
)
from plane.utils.github_app.assignee_mapping import map_assignees
from plane.utils.github_app.markdown import render_markdown as _render_markdown


def get_or_create_bot_user(workspace):
    """Bot user that owns GitHub-originated changes in a workspace."""
    hostname = urlparse(settings.WEB_URL or "https://plane.so").hostname or "plane.so"
    email = f"github-bot-{workspace.id}@{hostname}"
    user, _ = User.objects.get_or_create(
        email=email,
        defaults={
            "username": f"github_bot_{workspace.id}",
            "display_name": "GitHub",
            "first_name": "GitHub",
            "last_name": "",
            "is_bot": True,
            "bot_type": "GITHUB",
            "password": make_password(uuid.uuid4().hex),
            "is_password_autoset": True,
        },
    )
    return user


def upsert_installation(workspace, user, *, installation_id, account_login, account_type, target_id):
    """Create or revive the GithubAppInstallation row for a workspace + installation id.

    installation_id is globally unique, so reconnecting the same GitHub
    installation must revive its (possibly soft-deleted) row rather than
    violate the unique constraint. Switching a workspace to a different
    installation retires its previous active row first, to not violate the
    one-active-installation-per-workspace constraint.
    """
    existing = GithubAppInstallation.all_objects.filter(installation_id=installation_id).first()
    if existing:
        existing.deleted_at = None
        existing.workspace = workspace
        existing.account_login = account_login
        existing.account_type = account_type
        existing.target_id = target_id
        existing.installed_by = user
        existing.suspended_at = None
        existing.save()
        return existing

    GithubAppInstallation.objects.filter(workspace=workspace).exclude(installation_id=installation_id).delete()

    return GithubAppInstallation.objects.create(
        workspace=workspace,
        installation_id=installation_id,
        account_login=account_login,
        account_type=account_type,
        target_id=target_id,
        installed_by=user,
    )


def get_linked_repo(installation_id, repo_id):
    if installation_id is None or repo_id is None:
        return None
    return GithubLinkedRepository.objects.filter(
        installation__installation_id=installation_id, repo_id=repo_id, is_active=True
    ).first()


def get_state_mapping(project):
    return GithubProjectStateMapping.objects.filter(project=project).first()


def parse_gh_datetime(value):
    if not value:
        return None
    parsed = parse_datetime(value)
    if parsed and timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.utc)
    return parsed


def is_stale(stored_updated_at, incoming_updated_at):
    """True if an incoming event is older than the last update we recorded."""
    if not stored_updated_at or not incoming_updated_at:
        return False
    return incoming_updated_at < stored_updated_at


def render_markdown(text):
    return _render_markdown(text)


def body_hash(text):
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def move_issue_state(issue, new_state, actor):
    """Move a work item to a new state, recording an IssueActivity entry."""
    if new_state is None or issue.state_id == new_state.id:
        return
    old_state = issue.state
    issue.state = new_state
    issue.save(update_fields=["state", "completed_at", "updated_at"])
    IssueActivity.objects.create(
        workspace=issue.workspace,
        project=issue.project,
        issue=issue,
        actor=actor,
        verb="updated",
        field="state",
        old_value=old_state.name if old_state else "",
        new_value=new_state.name,
        old_identifier=old_state.id if old_state else None,
        new_identifier=new_state.id,
        comment=f"updated the state to {new_state.name} via GitHub",
    )


def record_github_activity(issue, actor, verb, comment):
    IssueActivity.objects.create(
        workspace=issue.workspace,
        project=issue.project,
        issue=issue,
        actor=actor,
        verb=verb,
        field="github",
        comment=comment,
    )


def ensure_bot_project_membership(project, bot_user):
    """Make the GitHub bot an active member of the workspace and project it writes to.

    Without this, the bot (as `created_by` on imported issues) is not a
    ProjectMember, so queries that join assignees through `member_project`
    (e.g. the assignee_ids annotation used while saving issue edits) can
    behave as if the issue has no valid participants, making the assignee
    field on bot-created issues effectively uneditable.
    """
    WorkspaceMember.objects.get_or_create(
        workspace=project.workspace, member=bot_user, defaults={"role": 15, "is_active": True}
    )
    ProjectMember.objects.get_or_create(
        project=project, member=bot_user, defaults={"workspace": project.workspace, "role": 15, "is_active": True}
    )


def sync_issue_assignees(issue, project, gh_assignees, issue_link, client=None, cache=None):
    """Full resync of an issue's Plane assignees from GitHub's current assignee list.

    Stores every GitHub login on `issue_link.assignee_logins` (each tagged with
    whether it mapped to a Plane user) so the work item's GitHub section can
    display them, unmapped ones included. Only mapped users whose login was
    added or removed since the previous sync are touched, so a Plane-side
    manual assignee who happens to be unmapped on GitHub is never removed by
    an unrelated GitHub unassign.
    """
    mapped, unmapped_logins = map_assignees(project, gh_assignees, client=client, cache=cache)
    new_logins = set(mapped) | set(unmapped_logins)

    previous_entries = issue_link.assignee_logins or []
    previous_by_login = {entry["login"]: entry for entry in previous_entries}
    previously_mapped_logins = {login for login, entry in previous_by_login.items() if entry.get("mapped")}

    for login in set(mapped) - previously_mapped_logins:
        IssueAssignee.objects.get_or_create(
            issue=issue,
            assignee=mapped[login],
            defaults={
                "project": project,
                "workspace": project.workspace,
                "created_by_id": issue.created_by_id,
                "updated_by_id": issue.created_by_id,
            },
        )

    removed_user_ids = [
        previous_by_login[login]["user_id"]
        for login in previously_mapped_logins - new_logins
        if previous_by_login[login].get("user_id")
    ]
    if removed_user_ids:
        IssueAssignee.objects.filter(issue=issue, assignee_id__in=removed_user_ids).delete()

    issue_link.assignee_logins = [
        {"login": login, "mapped": login in mapped, "user_id": str(mapped[login].id) if login in mapped else None}
        for login in sorted(new_logins)
    ]
    issue_link.save(update_fields=["assignee_logins", "updated_at"])


def match_labels(project, label_names):
    """Match GitHub label names to existing project Labels, case-insensitively."""
    from django.db.models import Q

    from plane.db.models import Label

    if not label_names:
        return []
    query = Q()
    for name in label_names:
        query |= Q(name__iexact=name)
    return list(Label.objects.filter(project=project).filter(query))
