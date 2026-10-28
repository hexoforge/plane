# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import pytest
from django.utils import timezone

from plane.bgtasks.github_app.handlers import handle_issue_comment
from plane.bgtasks.github_app.sync import body_hash
from plane.db.models import GithubCommentLink, GithubIssueLink, Issue, IssueComment, State

from .conftest import comment_payload


@pytest.fixture
def issue_link(db, linked_repo, project):
    state = State.objects.get(project=project, group="backlog")
    issue = Issue.objects.create(project=project, name="Something broke", state=state)
    return GithubIssueLink.objects.create(
        project=project,
        issue=issue,
        linked_repo=linked_repo,
        gh_issue_id=8001,
        gh_issue_number=42,
        url="https://github.com/acme/widgets/issues/42",
        gh_state="open",
        gh_updated_at=timezone.now(),
    )


@pytest.mark.unit
@pytest.mark.django_db
class TestHandleIssueComment:
    def test_created_adds_issue_comment(self, issue_link):
        result = handle_issue_comment(comment_payload())
        assert result == "processed"
        link = GithubCommentLink.objects.get(gh_comment_id=9001)
        assert link.source == "github"
        assert link.issue_comment.issue_id == issue_link.issue_id
        assert link.issue_comment.external_source == "github"
        assert link.issue_comment.external_id == "9001"

    def test_created_is_idempotent_on_redelivery(self, issue_link):
        handle_issue_comment(comment_payload())
        handle_issue_comment(comment_payload())
        assert IssueComment.objects.filter(external_id="9001").count() == 1

    def test_echo_of_plane_originated_comment_is_skipped(self, issue_link):
        comment = IssueComment.objects.create(project=issue_link.project, issue=issue_link.issue, comment_html="<p>hi</p>")
        GithubCommentLink.objects.create(
            workspace=issue_link.workspace,
            issue_comment=comment,
            issue_link=issue_link,
            gh_comment_id=9001,
            source="plane",
            last_synced_hash=body_hash("hi"),
        )
        result = handle_issue_comment(comment_payload())
        assert result == "skipped"
        assert IssueComment.objects.filter(external_source="github").count() == 0

    def test_edit_ping_pong_is_prevented_by_hash(self, issue_link):
        handle_issue_comment(comment_payload())
        link = GithubCommentLink.objects.get(gh_comment_id=9001)
        # Same body re-delivered as an "edited" event (e.g. GitHub echoing our
        # own write) must not be treated as a real edit.
        result = handle_issue_comment(comment_payload(action="edited"))
        assert result == "skipped"
        link.refresh_from_db()

    def test_edit_with_new_body_updates_comment(self, issue_link):
        handle_issue_comment(comment_payload())
        result = handle_issue_comment(comment_payload(action="edited", comment={**comment_payload()["comment"], "body": "updated"}))
        assert result == "processed"
        link = GithubCommentLink.objects.get(gh_comment_id=9001)
        assert "updated" in link.issue_comment.comment_html

    def test_delete_soft_deletes_comment(self, issue_link):
        handle_issue_comment(comment_payload())
        result = handle_issue_comment(comment_payload(action="deleted"))
        assert result == "processed"
        assert not IssueComment.objects.filter(external_id="9001").exists()
        assert not GithubCommentLink.objects.filter(gh_comment_id=9001).exists()

    def test_unknown_issue_is_skipped(self, linked_repo):
        result = handle_issue_comment(comment_payload(issue={"number": 999}))
        assert result == "skipped"

    def test_pull_request_comment_is_skipped(self, issue_link):
        payload = comment_payload(issue={"number": 42, "pull_request": {"url": "x"}})
        assert handle_issue_comment(payload) == "skipped"
