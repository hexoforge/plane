# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import pytest

from plane.bgtasks.github_app.handlers import handle_pull_request
from plane.db.models import GithubProjectStateMapping, GithubPullRequestLink, Issue, State

from .conftest import pr_payload


@pytest.fixture
def issue(db, project):
    state = State.objects.get(project=project, group="backlog")
    return Issue.objects.create(project=project, name="Something broke", state=state)


@pytest.fixture
def state_mapping(db, project):
    return GithubProjectStateMapping.objects.create(
        project=project,
        pr_opened_state=State.objects.get(project=project, group="started"),
        pr_merged_state=State.objects.get(project=project, group="completed"),
        issue_closed_state=State.objects.get(project=project, group="completed"),
        issue_reopened_state=State.objects.get(project=project, group="unstarted"),
    )


@pytest.mark.unit
@pytest.mark.django_db
class TestHandlePullRequest:
    def test_no_linked_repo_is_skipped(self, issue):
        result = handle_pull_request(pr_payload(repository={"id": 999999, "full_name": "x/y"}))
        assert result == "skipped"
        assert GithubPullRequestLink.objects.count() == 0

    def test_no_ref_in_title_or_body_is_skipped(self, linked_repo, issue):
        payload = pr_payload(
            pull_request={
                **pr_payload()["pull_request"],
                "title": "unrelated",
                "body": "none",
                "head": {"ref": "unrelated-branch"},
            }
        )
        assert handle_pull_request(payload) == "skipped"
        assert GithubPullRequestLink.objects.count() == 0

    def test_opened_links_and_moves_state(self, linked_repo, issue, state_mapping):
        result = handle_pull_request(pr_payload())
        assert result == "processed"
        link = GithubPullRequestLink.objects.get(issue=issue, pr_id=7001)
        assert link.state == "open"
        issue.refresh_from_db()
        assert issue.state_id == state_mapping.pr_opened_state_id

    def test_draft_links_without_state_move(self, linked_repo, issue, state_mapping):
        original_state_id = issue.state_id
        payload = pr_payload(pull_request={**pr_payload()["pull_request"], "draft": True})
        handle_pull_request(payload)
        link = GithubPullRequestLink.objects.get(issue=issue, pr_id=7001)
        assert link.state == "draft"
        issue.refresh_from_db()
        assert issue.state_id == original_state_id

    def test_ready_for_review_moves_state(self, linked_repo, issue, state_mapping):
        handle_pull_request(pr_payload(pull_request={**pr_payload()["pull_request"], "draft": True}))
        handle_pull_request(
            pr_payload(
                action="ready_for_review",
                pull_request={
                    **pr_payload()["pull_request"],
                    "draft": False,
                    "updated_at": "2024-01-02T00:00:00Z",
                },
            )
        )
        issue.refresh_from_db()
        assert issue.state_id == state_mapping.pr_opened_state_id

    def test_closed_merged_moves_to_merged_state(self, linked_repo, issue, state_mapping):
        handle_pull_request(pr_payload())
        handle_pull_request(
            pr_payload(
                action="closed",
                pull_request={
                    **pr_payload()["pull_request"],
                    "state": "closed",
                    "merged": True,
                    "merged_at": "2024-01-02T00:00:00Z",
                    "updated_at": "2024-01-02T00:00:00Z",
                },
            )
        )
        link = GithubPullRequestLink.objects.get(issue=issue, pr_id=7001)
        assert link.state == "merged"
        issue.refresh_from_db()
        assert issue.state_id == state_mapping.pr_merged_state_id

    def test_closed_unmerged_updates_link_only(self, linked_repo, issue, state_mapping):
        handle_pull_request(pr_payload())
        issue.refresh_from_db()
        opened_state_id = issue.state_id
        handle_pull_request(
            pr_payload(
                action="closed",
                pull_request={
                    **pr_payload()["pull_request"],
                    "state": "closed",
                    "merged": False,
                    "updated_at": "2024-01-02T00:00:00Z",
                },
            )
        )
        link = GithubPullRequestLink.objects.get(issue=issue, pr_id=7001)
        assert link.state == "closed"
        issue.refresh_from_db()
        assert issue.state_id == opened_state_id

    def test_out_of_order_event_is_ignored(self, linked_repo, issue, state_mapping):
        handle_pull_request(
            pr_payload(
                action="closed",
                pull_request={
                    **pr_payload()["pull_request"],
                    "state": "closed",
                    "merged": True,
                    "merged_at": "2024-01-05T00:00:00Z",
                    "updated_at": "2024-01-05T00:00:00Z",
                },
            )
        )
        # A stale "synchronize" event that is older than the merge must not
        # move the link backwards.
        handle_pull_request(
            pr_payload(action="synchronize", pull_request={**pr_payload()["pull_request"], "updated_at": "2024-01-01T00:00:00Z"})
        )
        link = GithubPullRequestLink.objects.get(issue=issue, pr_id=7001)
        assert link.state == "merged"

    def test_never_moves_back_from_merged(self, linked_repo, issue, state_mapping):
        handle_pull_request(
            pr_payload(
                action="closed",
                pull_request={
                    **pr_payload()["pull_request"],
                    "state": "closed",
                    "merged": True,
                    "merged_at": "2024-01-02T00:00:00Z",
                    "updated_at": "2024-01-02T00:00:00Z",
                },
            )
        )
        # A later-timestamped "reopened" event must still not undo the merge.
        handle_pull_request(
            pr_payload(action="reopened", pull_request={**pr_payload()["pull_request"], "updated_at": "2024-01-03T00:00:00Z"})
        )
        link = GithubPullRequestLink.objects.get(issue=issue, pr_id=7001)
        assert link.state == "merged"
        issue.refresh_from_db()
        assert issue.state_id == state_mapping.pr_merged_state_id
