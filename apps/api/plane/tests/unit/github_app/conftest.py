# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import pytest

from plane.db.models import GithubAppInstallation, GithubLinkedRepository, Project, ProjectMember, State


@pytest.fixture
def project(db, workspace, create_user):
    project = Project.objects.create(
        name="Github Project", identifier="GH", workspace=workspace, created_by=create_user
    )
    ProjectMember.objects.create(project=project, member=create_user, workspace=workspace, role=20)
    State.objects.create(name="Backlog", project=project, group="backlog", default=True)
    State.objects.create(name="Todo", project=project, group="unstarted")
    State.objects.create(name="In Progress", project=project, group="started")
    State.objects.create(name="Done", project=project, group="completed")
    State.objects.create(name="Cancelled", project=project, group="cancelled")
    return project


@pytest.fixture
def installation(db, workspace, create_user):
    return GithubAppInstallation.objects.create(
        workspace=workspace,
        installation_id=123456,
        account_login="acme",
        account_type="Organization",
        target_id=999,
        installed_by=create_user,
    )


@pytest.fixture
def linked_repo(db, project, installation):
    return GithubLinkedRepository.objects.create(
        project=project,
        installation=installation,
        repo_id=555,
        full_name="acme/widgets",
        private=False,
        default_branch="main",
        html_url="https://github.com/acme/widgets",
    )


def pr_payload(**overrides):
    payload = {
        "action": "opened",
        "installation": {"id": 123456},
        "repository": {"id": 555, "full_name": "acme/widgets"},
        "pull_request": {
            "id": 7001,
            "number": 12,
            "title": "Fix GH-1",
            "body": "closes GH-1",
            "html_url": "https://github.com/acme/widgets/pull/12",
            "state": "open",
            "draft": False,
            "merged": False,
            "merged_at": None,
            "updated_at": "2024-01-01T00:00:00Z",
            "head": {"ref": "fix/gh-1"},
            "user": {"login": "octocat", "avatar_url": "https://example.com/a.png"},
        },
    }
    payload.update(overrides)
    return payload


def issue_payload(**overrides):
    payload = {
        "action": "opened",
        "installation": {"id": 123456},
        "repository": {"id": 555, "full_name": "acme/widgets"},
        "issue": {
            "id": 8001,
            "number": 42,
            "title": "Something broke",
            "body": "It broke.",
            "html_url": "https://github.com/acme/widgets/issues/42",
            "state": "open",
            "updated_at": "2024-01-01T00:00:00Z",
            "labels": [],
        },
    }
    payload.update(overrides)
    return payload


def comment_payload(**overrides):
    payload = {
        "action": "created",
        "installation": {"id": 123456},
        "repository": {"id": 555, "full_name": "acme/widgets"},
        "issue": {"number": 42},
        "comment": {
            "id": 9001,
            "body": "a comment",
            "html_url": "https://github.com/acme/widgets/issues/42#issuecomment-9001",
            "updated_at": "2024-01-01T00:00:00Z",
        },
    }
    payload.update(overrides)
    return payload
