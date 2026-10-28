# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import pytest

from plane.bgtasks.github_app.handlers import handle_issues
from plane.db.models import GithubIssueLink, GithubProjectStateMapping, Label, State

from .conftest import issue_payload


@pytest.fixture
def state_mapping(db, project):
    return GithubProjectStateMapping.objects.create(
        project=project,
        issue_closed_state=State.objects.get(project=project, group="completed"),
        issue_reopened_state=State.objects.get(project=project, group="unstarted"),
    )


@pytest.mark.unit
@pytest.mark.django_db
class TestHandleIssues:
    def test_opened_auto_creates_work_item(self, linked_repo):
        result = handle_issues(issue_payload())
        assert result == "processed"
        link = GithubIssueLink.objects.get(linked_repo=linked_repo, gh_issue_number=42)
        assert link.issue.name == "Something broke"
        assert "<p>" in link.issue.description_html

    def test_opened_matches_existing_labels_case_insensitive(self, linked_repo, project):
        Label.objects.create(project=project, name="Bug")
        handle_issues(issue_payload(issue={**issue_payload()["issue"], "labels": [{"name": "bug"}]}))
        link = GithubIssueLink.objects.get(linked_repo=linked_repo, gh_issue_number=42)
        assert link.issue.labels.filter(name="Bug").exists()

    def test_auto_create_disabled_skips_creation(self, linked_repo, project):
        GithubProjectStateMapping.objects.create(project=project, auto_create_issues=False)
        result = handle_issues(issue_payload())
        assert result == "skipped"
        assert not GithubIssueLink.objects.filter(linked_repo=linked_repo, gh_issue_number=42).exists()

    def test_edited_before_opened_creates_then_updates(self, linked_repo):
        result = handle_issues(issue_payload(action="edited"))
        assert result == "processed"
        assert GithubIssueLink.objects.filter(linked_repo=linked_repo, gh_issue_number=42).exists()

    def test_edited_updates_name_and_description(self, linked_repo):
        handle_issues(issue_payload())
        handle_issues(
            issue_payload(
                action="edited",
                issue={**issue_payload()["issue"], "title": "New title", "updated_at": "2024-01-02T00:00:00Z"},
            )
        )
        link = GithubIssueLink.objects.get(linked_repo=linked_repo, gh_issue_number=42)
        assert link.issue.name == "New title"

    def test_stale_edit_is_ignored(self, linked_repo):
        handle_issues(issue_payload(issue={**issue_payload()["issue"], "updated_at": "2024-01-05T00:00:00Z"}))
        result = handle_issues(
            issue_payload(
                action="edited",
                issue={**issue_payload()["issue"], "title": "Should not apply", "updated_at": "2024-01-01T00:00:00Z"},
            )
        )
        assert result == "skipped"
        link = GithubIssueLink.objects.get(linked_repo=linked_repo, gh_issue_number=42)
        assert link.issue.name == "Something broke"

    def test_closed_moves_to_closed_state(self, linked_repo, state_mapping):
        handle_issues(issue_payload())
        handle_issues(
            issue_payload(
                action="closed",
                issue={**issue_payload()["issue"], "state": "closed", "updated_at": "2024-01-02T00:00:00Z"},
            )
        )
        link = GithubIssueLink.objects.get(linked_repo=linked_repo, gh_issue_number=42)
        assert link.issue.state_id == state_mapping.issue_closed_state_id
        assert link.gh_state == "closed"
        # Moving into a completed-group state stamps completed_at (as Issue.save does).
        link.issue.refresh_from_db()
        assert link.issue.completed_at is not None

    def test_reopened_moves_to_reopened_state(self, linked_repo, state_mapping):
        handle_issues(issue_payload())
        handle_issues(
            issue_payload(
                action="closed",
                issue={**issue_payload()["issue"], "state": "closed", "updated_at": "2024-01-02T00:00:00Z"},
            )
        )
        handle_issues(
            issue_payload(
                action="reopened",
                issue={**issue_payload()["issue"], "state": "open", "updated_at": "2024-01-03T00:00:00Z"},
            )
        )
        link = GithubIssueLink.objects.get(linked_repo=linked_repo, gh_issue_number=42)
        assert link.issue.state_id == state_mapping.issue_reopened_state_id
        # Leaving the completed group clears completed_at.
        link.issue.refresh_from_db()
        assert link.issue.completed_at is None

    def test_closed_without_state_mapping_does_not_crash(self, linked_repo, project):
        # No GithubProjectStateMapping configured for this project.
        handle_issues(issue_payload())
        result = handle_issues(
            issue_payload(
                action="closed",
                issue={**issue_payload()["issue"], "state": "closed", "updated_at": "2024-01-02T00:00:00Z"},
            )
        )
        assert result == "processed"
        link = GithubIssueLink.objects.get(linked_repo=linked_repo, gh_issue_number=42)
        assert link.gh_state == "closed"

    def test_labeled_adds_matching_label(self, linked_repo, project):
        handle_issues(issue_payload())
        Label.objects.create(project=project, name="Needs Triage")
        handle_issues(
            {
                **issue_payload(action="labeled"),
                "label": {"name": "needs triage"},
            }
        )
        link = GithubIssueLink.objects.get(linked_repo=linked_repo, gh_issue_number=42)
        assert link.issue.labels.filter(name="Needs Triage").exists()

    def test_pull_request_issue_event_is_skipped(self, linked_repo):
        payload = issue_payload(issue={**issue_payload()["issue"], "pull_request": {"url": "x"}})
        assert handle_issues(payload) == "skipped"
