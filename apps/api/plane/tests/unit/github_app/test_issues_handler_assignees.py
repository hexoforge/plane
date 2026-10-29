# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import pytest

from plane.bgtasks.github_app.handlers import handle_issues
from plane.db.models import (
    Account,
    GithubIssueLink,
    GithubProjectStateMapping,
    IssueAssignee,
    ProjectMember,
    State,
    WorkspaceMember,
)
from plane.tests.factories import UserFactory

from .conftest import issue_payload


def _add_member(project, login, gh_id):
    user = UserFactory()
    ProjectMember.objects.create(project=project, member=user, workspace=project.workspace, role=15)
    Account.objects.create(user=user, provider="github", provider_account_id=str(gh_id))
    return user


@pytest.mark.unit
@pytest.mark.django_db
class TestIssueAssigneeSync:
    def test_opened_sets_initial_assignees(self, linked_repo, project):
        member = _add_member(project, "octocat", 501)

        handle_issues(issue_payload(issue={**issue_payload()["issue"], "assignees": [{"id": 501, "login": "octocat"}]}))

        link = GithubIssueLink.objects.get(linked_repo=linked_repo, gh_issue_number=42)
        assert IssueAssignee.objects.filter(issue=link.issue, assignee=member).exists()
        assert link.assignee_logins == [{"login": "octocat", "mapped": True, "user_id": str(member.id)}]

    def test_assigned_action_adds_assignee(self, linked_repo, project):
        handle_issues(issue_payload())
        member = _add_member(project, "octocat", 501)

        handle_issues(
            issue_payload(
                action="assigned",
                issue={
                    **issue_payload()["issue"],
                    "assignees": [{"id": 501, "login": "octocat"}],
                    "updated_at": "2024-01-02T00:00:00Z",
                },
            )
        )

        link = GithubIssueLink.objects.get(linked_repo=linked_repo, gh_issue_number=42)
        assert IssueAssignee.objects.filter(issue=link.issue, assignee=member).exists()

    def test_unassigned_action_removes_assignee(self, linked_repo, project):
        member = _add_member(project, "octocat", 501)
        handle_issues(issue_payload(issue={**issue_payload()["issue"], "assignees": [{"id": 501, "login": "octocat"}]}))
        link = GithubIssueLink.objects.get(linked_repo=linked_repo, gh_issue_number=42)
        assert IssueAssignee.objects.filter(issue=link.issue, assignee=member).exists()

        handle_issues(
            issue_payload(
                action="unassigned",
                issue={**issue_payload()["issue"], "assignees": [], "updated_at": "2024-01-02T00:00:00Z"},
            )
        )

        assert not IssueAssignee.objects.filter(issue=link.issue, assignee=member).exists()

    def test_unknown_login_is_unmapped_but_recorded(self, linked_repo, project):
        handle_issues(
            issue_payload(issue={**issue_payload()["issue"], "assignees": [{"id": 999, "login": "stranger"}]})
        )
        link = GithubIssueLink.objects.get(linked_repo=linked_repo, gh_issue_number=42)
        assert link.assignee_logins == [{"login": "stranger", "mapped": False, "user_id": None}]
        assert not IssueAssignee.objects.filter(issue=link.issue).exists()

    def test_manual_plane_assignee_of_unmapped_person_survives_unrelated_unassign(self, linked_repo, project):
        tracked = _add_member(project, "octocat", 501)
        other_person = UserFactory()
        ProjectMember.objects.create(project=project, member=other_person, workspace=project.workspace, role=15)

        handle_issues(
            issue_payload(
                issue={
                    **issue_payload()["issue"],
                    "assignees": [{"id": 501, "login": "octocat"}],
                }
            )
        )
        link = GithubIssueLink.objects.get(linked_repo=linked_repo, gh_issue_number=42)
        # A Plane admin manually assigns someone unrelated to any GitHub login.
        IssueAssignee.objects.create(
            issue=link.issue, assignee=other_person, project=project, workspace=project.workspace
        )

        # GitHub unassigns octocat; "other_person" was never GitHub-tracked and must not be touched.
        handle_issues(
            issue_payload(
                action="unassigned",
                issue={**issue_payload()["issue"], "assignees": [], "updated_at": "2024-01-02T00:00:00Z"},
            )
        )

        assert not IssueAssignee.objects.filter(issue=link.issue, assignee=tracked).exists()
        assert IssueAssignee.objects.filter(issue=link.issue, assignee=other_person).exists()

    def test_bot_becomes_active_project_member_on_issue_creation(self, linked_repo, project):
        handle_issues(issue_payload())
        link = GithubIssueLink.objects.get(linked_repo=linked_repo, gh_issue_number=42)
        bot_user = link.issue.created_by
        assert ProjectMember.objects.filter(project=project, member=bot_user, is_active=True).exists()
        assert WorkspaceMember.objects.filter(workspace=project.workspace, member=bot_user, is_active=True).exists()


@pytest.mark.unit
@pytest.mark.django_db
class TestClosedWhileAlreadyDone:
    def test_closed_does_not_move_an_already_completed_item(self, linked_repo, project):
        done_state = State.objects.get(project=project, group="completed")
        cancelled_state = State.objects.get(project=project, group="cancelled")
        GithubProjectStateMapping.objects.create(project=project, issue_closed_state=cancelled_state)

        handle_issues(issue_payload())
        link = GithubIssueLink.objects.get(linked_repo=linked_repo, gh_issue_number=42)
        link.issue.state = done_state
        link.issue.save(update_fields=["state", "updated_at"])

        handle_issues(
            issue_payload(
                action="closed",
                issue={**issue_payload()["issue"], "state": "closed", "updated_at": "2024-01-02T00:00:00Z"},
            )
        )

        link.issue.refresh_from_db()
        assert link.issue.state_id == done_state.id

    def test_closed_still_moves_an_unstarted_item(self, linked_repo, project):
        cancelled_state = State.objects.get(project=project, group="cancelled")
        GithubProjectStateMapping.objects.create(project=project, issue_closed_state=cancelled_state)

        handle_issues(issue_payload())
        link = GithubIssueLink.objects.get(linked_repo=linked_repo, gh_issue_number=42)

        handle_issues(
            issue_payload(
                action="closed",
                issue={**issue_payload()["issue"], "state": "closed", "updated_at": "2024-01-02T00:00:00Z"},
            )
        )

        link.issue.refresh_from_db()
        assert link.issue.state_id == cancelled_state.id
