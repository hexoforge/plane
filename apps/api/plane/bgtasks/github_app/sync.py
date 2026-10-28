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
    User,
)
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
