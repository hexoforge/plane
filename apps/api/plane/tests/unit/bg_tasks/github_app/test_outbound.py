# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from unittest.mock import Mock, patch

import pytest
from django.utils import timezone

from plane.bgtasks.github_app.outbound import sync_comment_to_github, sync_issue_state_to_github
from plane.db.models import (
    GithubAppInstallation,
    GithubCommentLink,
    GithubIssueLink,
    GithubLinkedRepository,
    GithubProjectStateMapping,
    Issue,
    IssueComment,
    State,
    StateGroup,
)
from plane.tests.factories import ProjectFactory, UserFactory


@pytest.fixture
def project():
    return ProjectFactory()


@pytest.fixture
def installation(project):
    return GithubAppInstallation.objects.create(
        workspace=project.workspace,
        installation_id=999,
        account_login="acme",
        account_type="Organization",
        target_id=1,
    )


@pytest.fixture
def linked_repo(project, installation):
    return GithubLinkedRepository.objects.create(
        workspace=project.workspace,
        project=project,
        installation=installation,
        repo_id=555,
        full_name="acme/widgets",
    )


def _make_state(project, group):
    return State.objects.create(project=project, name=f"state-{group}", color="#fff", group=group)


def _make_issue(project, state):
    return Issue.objects.create(project=project, name="Bug report", state=state)


def _make_issue_link(project, linked_repo, issue, gh_state="open"):
    return GithubIssueLink.objects.create(
        workspace=project.workspace,
        project=project,
        issue=issue,
        linked_repo=linked_repo,
        gh_issue_id=111,
        gh_issue_number=7,
        url="https://github.com/acme/widgets/issues/7",
        gh_state=gh_state,
        gh_updated_at=timezone.now(),
    )


def _github_bot_user(workspace):
    return UserFactory(username="github-bot-acme", is_bot=True)


@pytest.mark.django_db
class TestSyncIssueStateToGithub:
    def test_closes_github_issue_when_state_group_is_completed(self, project, linked_repo):
        state = _make_state(project, StateGroup.COMPLETED)
        issue = _make_issue(project, state)
        link = _make_issue_link(project, linked_repo, issue)

        with patch("plane.bgtasks.github_app.outbound.GithubAppClient") as MockClient:
            MockClient.return_value.update_issue_state.return_value = {"state": "closed"}
            sync_issue_state_to_github(issue_id=str(issue.id))

        MockClient.assert_called_once_with(linked_repo.installation.installation_id)
        MockClient.return_value.update_issue_state.assert_called_once_with(
            "acme/widgets", 7, "closed", "completed"
        )
        link.refresh_from_db()
        assert link.gh_state == "closed"

    def test_closes_with_not_planned_reason_when_cancelled(self, project, linked_repo):
        state = _make_state(project, StateGroup.CANCELLED)
        issue = _make_issue(project, state)
        _make_issue_link(project, linked_repo, issue)

        with patch("plane.bgtasks.github_app.outbound.GithubAppClient") as MockClient:
            MockClient.return_value.update_issue_state.return_value = {"state": "closed"}
            sync_issue_state_to_github(issue_id=str(issue.id))

        MockClient.return_value.update_issue_state.assert_called_once_with(
            "acme/widgets", 7, "closed", "not_planned"
        )

    def test_reopens_github_issue_when_state_group_leaves_completed(self, project, linked_repo):
        state = _make_state(project, StateGroup.STARTED)
        issue = _make_issue(project, state)
        link = _make_issue_link(project, linked_repo, issue, gh_state="closed")

        with patch("plane.bgtasks.github_app.outbound.GithubAppClient") as MockClient:
            MockClient.return_value.update_issue_state.return_value = {"state": "open"}
            sync_issue_state_to_github(issue_id=str(issue.id))

        MockClient.return_value.update_issue_state.assert_called_once_with("acme/widgets", 7, "open", None)
        link.refresh_from_db()
        assert link.gh_state == "open"

    def test_noop_when_issue_has_no_github_link(self, project):
        state = _make_state(project, StateGroup.COMPLETED)
        issue = _make_issue(project, state)

        with patch("plane.bgtasks.github_app.outbound.GithubAppClient") as MockClient:
            sync_issue_state_to_github(issue_id=str(issue.id))

        MockClient.assert_not_called()

    def test_skips_when_actor_is_the_github_bot_to_prevent_loops(self, project, linked_repo):
        state = _make_state(project, StateGroup.COMPLETED)
        issue = _make_issue(project, state)
        _make_issue_link(project, linked_repo, issue)
        bot = _github_bot_user(project.workspace)

        with patch("plane.bgtasks.github_app.outbound.GithubAppClient") as MockClient:
            sync_issue_state_to_github(issue_id=str(issue.id), actor_id=str(bot.id))

        MockClient.assert_not_called()


@pytest.mark.django_db
class TestSyncCommentToGithub:
    def _make_comment(self, project, issue, **kwargs):
        actor = kwargs.pop("actor", None) or UserFactory()
        return IssueComment.objects.create(
            project=project, issue=issue, actor=actor, comment_html="<p>hello</p>", **kwargs
        )

    def _setup_issue(self, project, linked_repo):
        state = _make_state(project, StateGroup.BACKLOG)
        issue = _make_issue(project, state)
        link = _make_issue_link(project, linked_repo, issue)
        return issue, link

    def test_create_posts_comment_and_records_link(self, project, linked_repo):
        issue, link = self._setup_issue(project, linked_repo)
        comment = self._make_comment(project, issue)

        with patch("plane.bgtasks.github_app.outbound.GithubAppClient") as MockClient:
            MockClient.return_value.create_issue_comment.return_value = {"id": 4242}
            sync_comment_to_github(comment_id=str(comment.id), action="create")

        MockClient.return_value.create_issue_comment.assert_called_once_with("acme/widgets", 7, "hello")
        comment_link = GithubCommentLink.objects.get(issue_comment_id=comment.id)
        assert comment_link.gh_comment_id == 4242
        assert comment_link.source == "plane"

    def test_create_is_idempotent_when_link_already_exists(self, project, linked_repo):
        issue, link = self._setup_issue(project, linked_repo)
        comment = self._make_comment(project, issue)
        GithubCommentLink.objects.create(
            workspace=project.workspace,
            issue_comment=comment,
            issue_link=link,
            gh_comment_id=1,
            source="plane",
        )

        with patch("plane.bgtasks.github_app.outbound.GithubAppClient") as MockClient:
            sync_comment_to_github(comment_id=str(comment.id), action="create")

        MockClient.return_value.create_issue_comment.assert_not_called()

    def test_update_skips_when_body_hash_unchanged(self, project, linked_repo):
        issue, link = self._setup_issue(project, linked_repo)
        comment = self._make_comment(project, issue)
        from plane.bgtasks.github_app.outbound import _hash_body

        GithubCommentLink.objects.create(
            workspace=project.workspace,
            issue_comment=comment,
            issue_link=link,
            gh_comment_id=1,
            source="plane",
            last_synced_hash=_hash_body(comment.comment_stripped),
        )

        with patch("plane.bgtasks.github_app.outbound.GithubAppClient") as MockClient:
            sync_comment_to_github(comment_id=str(comment.id), action="update")

        MockClient.return_value.update_issue_comment.assert_not_called()

    def test_update_posts_when_body_changed(self, project, linked_repo):
        issue, link = self._setup_issue(project, linked_repo)
        comment = self._make_comment(project, issue)
        comment_link = GithubCommentLink.objects.create(
            workspace=project.workspace,
            issue_comment=comment,
            issue_link=link,
            gh_comment_id=1,
            source="plane",
            last_synced_hash="stale-hash",
        )

        with patch("plane.bgtasks.github_app.outbound.GithubAppClient") as MockClient:
            sync_comment_to_github(comment_id=str(comment.id), action="update")

        MockClient.return_value.update_issue_comment.assert_called_once_with("acme/widgets", 1, "hello")
        comment_link.refresh_from_db()
        assert comment_link.last_synced_hash != "stale-hash"

    def test_delete_removes_github_comment_and_link(self, project, linked_repo):
        issue, link = self._setup_issue(project, linked_repo)
        comment = self._make_comment(project, issue)
        GithubCommentLink.objects.create(
            workspace=project.workspace,
            issue_comment=comment,
            issue_link=link,
            gh_comment_id=99,
            source="plane",
        )
        comment.delete()

        with patch("plane.bgtasks.github_app.outbound.GithubAppClient") as MockClient:
            sync_comment_to_github(comment_id=str(comment.id), action="delete")

        MockClient.return_value.delete_issue_comment.assert_called_once_with("acme/widgets", 99)
        assert not GithubCommentLink.objects.filter(issue_comment_id=comment.id).exists()

    def test_skips_when_comment_came_from_github(self, project, linked_repo):
        issue, link = self._setup_issue(project, linked_repo)
        comment = self._make_comment(project, issue, external_source="github")

        with patch("plane.bgtasks.github_app.outbound.GithubAppClient") as MockClient:
            sync_comment_to_github(comment_id=str(comment.id), action="create")

        MockClient.assert_not_called()

    def test_skips_when_actor_is_the_github_bot_to_prevent_loops(self, project, linked_repo):
        issue, link = self._setup_issue(project, linked_repo)
        bot = _github_bot_user(project.workspace)
        comment = self._make_comment(project, issue, actor=bot)

        with patch("plane.bgtasks.github_app.outbound.GithubAppClient") as MockClient:
            sync_comment_to_github(comment_id=str(comment.id), action="create")

        MockClient.assert_not_called()

    def test_skips_when_project_mapping_disables_comment_sync(self, project, linked_repo):
        issue, link = self._setup_issue(project, linked_repo)
        comment = self._make_comment(project, issue)
        GithubProjectStateMapping.objects.create(workspace=project.workspace, project=project, sync_comments=False)

        with patch("plane.bgtasks.github_app.outbound.GithubAppClient") as MockClient:
            sync_comment_to_github(comment_id=str(comment.id), action="create")

        MockClient.assert_not_called()
