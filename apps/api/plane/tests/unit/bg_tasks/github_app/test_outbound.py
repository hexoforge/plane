# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from unittest.mock import patch

import pytest
from django.utils import timezone

from plane.bgtasks.github_app.outbound import (
    sync_comment_to_github,
    sync_issue_assignees_to_github,
    sync_issue_state_to_github,
)
from plane.db.models import (
    Account,
    GithubAppInstallation,
    GithubCommentLink,
    GithubIssueLink,
    GithubLinkedRepository,
    GithubProjectStateMapping,
    Issue,
    IssueAssignee,
    IssueComment,
    State,
    StateGroup,
)
from plane.tests.factories import ProjectFactory, ProjectMemberFactory, UserFactory


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
    # Mirror the real get_or_create_bot_user: the loop guard keys off bot_type,
    # not the username (which uses an underscore, not the "github-bot-" email prefix).
    return UserFactory(username=f"github_bot_{workspace.id}", is_bot=True, bot_type="GITHUB")


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

    def test_create_posts_markdown_converted_from_html_not_plain_text(self, project, linked_repo):
        issue, link = self._setup_issue(project, linked_repo)
        comment = IssueComment.objects.create(
            project=project, issue=issue, actor=UserFactory(), comment_html="<p><strong>bold</strong> text</p>"
        )

        with patch("plane.bgtasks.github_app.outbound.GithubAppClient") as MockClient:
            MockClient.return_value.create_issue_comment.return_value = {"id": 4242}
            sync_comment_to_github(comment_id=str(comment.id), action="create")

        MockClient.return_value.create_issue_comment.assert_called_once_with("acme/widgets", 7, "**bold** text")

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


@pytest.mark.django_db
class TestSyncIssueAssigneesToGithub:
    def _setup_issue(self, project, linked_repo, assignee_logins=None):
        state = _make_state(project, StateGroup.BACKLOG)
        issue = _make_issue(project, state)
        link = _make_issue_link(project, linked_repo, issue)
        if assignee_logins is not None:
            link.assignee_logins = assignee_logins
            link.save(update_fields=["assignee_logins"])
        return issue, link

    def test_noop_when_toggle_is_off_by_default(self, project, linked_repo):
        issue, link = self._setup_issue(project, linked_repo)

        with patch("plane.bgtasks.github_app.outbound.GithubAppClient") as MockClient:
            sync_issue_assignees_to_github(issue_id=str(issue.id))

        MockClient.assert_not_called()

    def test_pushes_mapped_assignee_login_when_enabled(self, project, linked_repo):
        issue, link = self._setup_issue(project, linked_repo)
        GithubProjectStateMapping.objects.create(workspace=project.workspace, project=project, sync_assignees=True)
        member = UserFactory()
        ProjectMemberFactory(project=project, member=member, role=15)
        Account.objects.create(user=member, provider="github", provider_account_id="501")
        IssueAssignee.objects.create(issue=issue, assignee=member, project=project, workspace=project.workspace)

        with patch("plane.bgtasks.github_app.outbound.GithubAppClient") as MockClient:
            MockClient.return_value.get_user_by_id.return_value = {"login": "octocat"}
            MockClient.return_value.update_issue_assignees.return_value = {
                "assignees": [{"login": "octocat"}]
            }
            sync_issue_assignees_to_github(issue_id=str(issue.id))

        MockClient.return_value.update_issue_assignees.assert_called_once_with("acme/widgets", 7, {"octocat"})
        link.refresh_from_db()
        assert link.assignee_logins == [{"login": "octocat", "mapped": True, "user_id": str(member.id)}]

    def test_keeps_unmapped_github_assignee_untouched(self, project, linked_repo):
        issue, link = self._setup_issue(
            project, linked_repo, assignee_logins=[{"login": "stranger", "mapped": False, "user_id": None}]
        )
        GithubProjectStateMapping.objects.create(workspace=project.workspace, project=project, sync_assignees=True)
        member = UserFactory()
        ProjectMemberFactory(project=project, member=member, role=15)
        Account.objects.create(user=member, provider="github", provider_account_id="501")
        IssueAssignee.objects.create(issue=issue, assignee=member, project=project, workspace=project.workspace)

        with patch("plane.bgtasks.github_app.outbound.GithubAppClient") as MockClient:
            MockClient.return_value.get_user_by_id.return_value = {"login": "octocat"}
            MockClient.return_value.update_issue_assignees.return_value = {
                "assignees": [{"login": "octocat"}, {"login": "stranger"}]
            }
            sync_issue_assignees_to_github(issue_id=str(issue.id))

        MockClient.return_value.update_issue_assignees.assert_called_once_with(
            "acme/widgets", 7, {"octocat", "stranger"}
        )

    def test_noop_when_desired_set_already_matches_github(self, project, linked_repo):
        issue, link = self._setup_issue(
            project, linked_repo, assignee_logins=[{"login": "octocat", "mapped": True, "user_id": None}]
        )
        GithubProjectStateMapping.objects.create(workspace=project.workspace, project=project, sync_assignees=True)
        member = UserFactory()
        ProjectMemberFactory(project=project, member=member, role=15)
        Account.objects.create(user=member, provider="github", provider_account_id="501")
        IssueAssignee.objects.create(issue=issue, assignee=member, project=project, workspace=project.workspace)
        link.assignee_logins = [{"login": "octocat", "mapped": True, "user_id": str(member.id)}]
        link.save(update_fields=["assignee_logins"])

        with patch("plane.bgtasks.github_app.outbound.GithubAppClient") as MockClient:
            sync_issue_assignees_to_github(issue_id=str(issue.id))

        MockClient.return_value.update_issue_assignees.assert_not_called()

    def test_skips_when_actor_is_the_github_bot_to_prevent_loops(self, project, linked_repo):
        issue, link = self._setup_issue(project, linked_repo)
        GithubProjectStateMapping.objects.create(workspace=project.workspace, project=project, sync_assignees=True)
        bot = _github_bot_user(project.workspace)

        with patch("plane.bgtasks.github_app.outbound.GithubAppClient") as MockClient:
            sync_issue_assignees_to_github(issue_id=str(issue.id), actor_id=str(bot.id))

        MockClient.assert_not_called()

    def test_noop_when_issue_has_no_github_link(self, project):
        state = _make_state(project, StateGroup.BACKLOG)
        issue = _make_issue(project, state)

        with patch("plane.bgtasks.github_app.outbound.GithubAppClient") as MockClient:
            sync_issue_assignees_to_github(issue_id=str(issue.id))

        MockClient.assert_not_called()
