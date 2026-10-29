# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import io
from unittest.mock import Mock, patch

import pytest
from django.core.management import call_command

from plane.db.models import GithubCommentLink, GithubIssueLink, IssueActivity, IssueComment

from .conftest import issue_payload
from plane.bgtasks.github_app.handlers import handle_issues, handle_issue_comment

from .conftest import comment_payload


def _run_command(**options):
    out = io.StringIO()
    call_command("github_rerender_bodies", stdout=out, **options)
    return out.getvalue()


@pytest.mark.unit
@pytest.mark.django_db
class TestGithubRerenderBodiesCommand:
    def test_refetches_and_rerenders_from_github(self, linked_repo, project):
        handle_issues(issue_payload())
        link = GithubIssueLink.objects.get(linked_repo=linked_repo, gh_issue_number=42)
        # Simulate a body stored by an older/weaker renderer.
        link.issue.description_html = "<p>It broke.</p>"
        link.issue.save(update_fields=["description_html", "description_stripped", "updated_at"])

        client = Mock()
        client.get_issue.return_value = {"body": "# It broke\n\n- [ ] investigate"}
        with patch("plane.db.management.commands.github_rerender_bodies.GithubAppClient", return_value=client):
            _run_command()

        link.issue.refresh_from_db()
        assert "<h1>It broke</h1>" in link.issue.description_html
        assert 'data-type="taskList"' in link.issue.description_html
        assert link.issue.description_binary is None

    def test_dry_run_makes_no_changes(self, linked_repo, project):
        handle_issues(issue_payload())
        link = GithubIssueLink.objects.get(linked_repo=linked_repo, gh_issue_number=42)
        original_html = link.issue.description_html

        client = Mock()
        client.get_issue.return_value = {"body": "# Changed"}
        with patch("plane.db.management.commands.github_rerender_bodies.GithubAppClient", return_value=client):
            output = _run_command(dry_run=True)

        link.issue.refresh_from_db()
        assert link.issue.description_html == original_html
        assert "rendered=1" in output

    def test_skips_issue_edited_in_plane_after_import(self, linked_repo, project):
        handle_issues(issue_payload())
        link = GithubIssueLink.objects.get(linked_repo=linked_repo, gh_issue_number=42)
        original_html = link.issue.description_html
        IssueActivity.objects.create(
            workspace=project.workspace,
            project=project,
            issue=link.issue,
            actor=project.created_by,
            verb="updated",
            field="description",
            comment="updated the description",
        )

        client = Mock()
        client.get_issue.return_value = {"body": "# Changed on GitHub"}
        with patch("plane.db.management.commands.github_rerender_bodies.GithubAppClient", return_value=client):
            output = _run_command()

        link.issue.refresh_from_db()
        assert link.issue.description_html == original_html
        assert "skipped_edited_in_plane=1" in output

    def test_idempotent_second_run_reports_unchanged(self, linked_repo, project):
        handle_issues(issue_payload())

        client = Mock()
        client.get_issue.return_value = {"body": "Rendered body"}
        with patch("plane.db.management.commands.github_rerender_bodies.GithubAppClient", return_value=client):
            first_output = _run_command()
            second_output = _run_command()

        assert "rendered=1" in first_output
        assert "rendered=0" in second_output
        assert "unchanged=1" in second_output

    def test_falls_back_to_stored_plain_text_when_refetch_fails(self, linked_repo, project):
        handle_issues(issue_payload())
        link = GithubIssueLink.objects.get(linked_repo=linked_repo, gh_issue_number=42)
        link.issue.description_html = "<p>stale</p>"
        link.issue.save(update_fields=["description_html", "description_stripped", "updated_at"])
        stripped_before = link.issue.description_stripped

        client = Mock()
        client.get_issue.side_effect = RuntimeError("installation revoked")
        with patch("plane.db.management.commands.github_rerender_bodies.GithubAppClient", return_value=client):
            _run_command()

        link.issue.refresh_from_db()
        assert stripped_before in link.issue.description_html

    def test_filters_by_project(self, linked_repo, project):
        handle_issues(issue_payload())
        link = GithubIssueLink.objects.get(linked_repo=linked_repo, gh_issue_number=42)

        client = Mock()
        client.get_issue.return_value = {"body": "Changed"}
        with patch("plane.db.management.commands.github_rerender_bodies.GithubAppClient", return_value=client):
            output = _run_command(project="00000000-0000-0000-0000-000000000000")

        link.issue.refresh_from_db()
        assert "rendered=0" in output
        assert "<p>It broke" in link.issue.description_html

    def test_rerenders_github_sourced_comments(self, linked_repo, project):
        handle_issues(issue_payload())
        handle_issue_comment(comment_payload())
        comment_link = GithubCommentLink.objects.get(source="github")
        comment_link.issue_comment.comment_html = "<p>stale</p>"
        comment_link.issue_comment.save(update_fields=["comment_html", "comment_stripped", "updated_at"])

        client = Mock()
        client.get_issue.return_value = {"body": "It broke."}
        client.get_issue_comment.return_value = {"body": "**updated** comment"}
        with patch("plane.db.management.commands.github_rerender_bodies.GithubAppClient", return_value=client):
            output = _run_command()

        comment = IssueComment.objects.get(pk=comment_link.issue_comment_id)
        assert "<strong>updated</strong>" in comment.comment_html
        assert "comments: rendered=1" in output
