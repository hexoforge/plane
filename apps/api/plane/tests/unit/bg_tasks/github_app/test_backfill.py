# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from unittest.mock import Mock, patch

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from plane.bgtasks.github_app.backfill import (
    _link_pull_request,
    match_or_create_labels,
    run_github_backfill,
)
from plane.utils.github_app.assignee_mapping import map_assignees
from plane.db.models import (
    Account,
    GithubAppInstallation,
    GithubBackfillRun,
    GithubCommentLink,
    GithubIssueLink,
    GithubLinkedRepository,
    GithubProjectStateMapping,
    GithubPullRequestLink,
    Issue,
    IssueActivity,
    IssueComment,
    Label,
    ProjectMember,
    State,
)
from plane.tests.factories import ProjectFactory, UserFactory


@pytest.fixture
def project():
    project = ProjectFactory()
    project.identifier = "GH"
    project.save()
    return project


@pytest.fixture
def states(project):
    backlog = State.objects.create(project=project, name="Backlog", color="#000", group="backlog", default=True)
    done = State.objects.create(project=project, name="Done", color="#000", group="completed")
    return {"backlog": backlog, "done": done}


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
        project=project,
        installation=installation,
        repo_id=555,
        full_name="acme/widgets",
        html_url="https://github.com/acme/widgets",
    )


def gh_issue(number, title="A bug", body="", state="open", labels=None, assignees=None):
    return {
        "id": 10_000 + number,
        "number": number,
        "title": title,
        "body": body,
        "html_url": f"https://github.com/acme/widgets/issues/{number}",
        "state": state,
        "updated_at": "2024-01-01T00:00:00Z",
        "labels": labels or [],
        "assignees": assignees or [],
    }


def gh_pr(number, title="", body="", state="open", merged_at=None, draft=False, head_ref=""):
    return {
        "id": 20_000 + number,
        "number": number,
        "title": title,
        "body": body,
        "html_url": f"https://github.com/acme/widgets/pull/{number}",
        "state": state,
        "draft": draft,
        "merged_at": merged_at,
        "updated_at": "2024-01-01T00:00:00Z",
        "head": {"ref": head_ref},
        "user": {"login": "octocat", "avatar_url": "https://example.com/a.png"},
    }


def make_client_mock(issues=None, pulls=None, comments=None):
    client = Mock()
    client.list_repo_issues.return_value = issues or []
    client.list_repo_pulls.return_value = pulls or []
    client.list_issue_comments.return_value = comments or []
    return client


@pytest.mark.unit
@pytest.mark.django_db
class TestRunGithubBackfillIdempotency:
    def test_rerunning_creates_no_duplicate_issues_or_comments(self, project, states, linked_repo):
        issue_payload = gh_issue(1, title="Something broke")
        comment_payload = {"id": 777, "body": "a comment"}

        for _ in range(2):
            run = GithubBackfillRun.objects.create(project=project, linked_repo=linked_repo)
            client = make_client_mock(issues=[issue_payload], comments=[comment_payload])
            with patch("plane.bgtasks.github_app.backfill.GithubAppClient", return_value=client):
                run_github_backfill(str(run.id))
            run.refresh_from_db()
            assert run.status == "completed"

        assert Issue.objects.filter(project=project).count() == 1
        assert IssueComment.objects.count() == 1
        assert GithubIssueLink.objects.filter(linked_repo=linked_repo).count() == 1
        assert GithubCommentLink.objects.count() == 1

    def test_failed_link_creation_rolls_back_issue_so_rerun_does_not_duplicate(self, project, states, linked_repo):
        issue_payload = gh_issue(1, title="Something broke")

        run = GithubBackfillRun.objects.create(project=project, linked_repo=linked_repo)
        client = make_client_mock(issues=[issue_payload])
        with patch("plane.bgtasks.github_app.backfill.GithubAppClient", return_value=client), patch.object(
            GithubIssueLink.objects, "create", side_effect=RuntimeError("db boom")
        ):
            run_github_backfill(str(run.id))

        # The issue.save() inside _import_issue must not survive a link failure.
        assert Issue.objects.filter(project=project).count() == 0
        assert GithubIssueLink.objects.filter(linked_repo=linked_repo).count() == 0

        run = GithubBackfillRun.objects.create(project=project, linked_repo=linked_repo)
        client = make_client_mock(issues=[issue_payload])
        with patch("plane.bgtasks.github_app.backfill.GithubAppClient", return_value=client):
            run_github_backfill(str(run.id))

        assert Issue.objects.filter(project=project).count() == 1
        assert GithubIssueLink.objects.filter(linked_repo=linked_repo).count() == 1

    def test_pull_requests_filters_out_issue_entries(self, project, states, linked_repo):
        run = GithubBackfillRun.objects.create(project=project, linked_repo=linked_repo)
        pr_like_issue = gh_issue(2)
        pr_like_issue["pull_request"] = {"url": "..."}
        client = make_client_mock(issues=[gh_issue(1), pr_like_issue])
        with patch("plane.bgtasks.github_app.backfill.GithubAppClient", return_value=client):
            run_github_backfill(str(run.id))

        assert Issue.objects.filter(project=project).count() == 1
        run.refresh_from_db()
        assert run.total_issues == 1


@pytest.mark.unit
@pytest.mark.django_db
class TestBackfillSkippedVsImportedCounts:
    def test_rerun_counts_already_linked_issues_as_skipped_not_imported(self, project, states, linked_repo):
        issue_payload = gh_issue(1, title="Something broke")

        first_run = GithubBackfillRun.objects.create(project=project, linked_repo=linked_repo)
        client = make_client_mock(issues=[issue_payload])
        with patch("plane.bgtasks.github_app.backfill.GithubAppClient", return_value=client):
            run_github_backfill(str(first_run.id))
        first_run.refresh_from_db()
        assert first_run.imported_issues == 1
        assert first_run.skipped_issues == 0

        second_run = GithubBackfillRun.objects.create(project=project, linked_repo=linked_repo)
        client = make_client_mock(issues=[issue_payload])
        with patch("plane.bgtasks.github_app.backfill.GithubAppClient", return_value=client):
            run_github_backfill(str(second_run.id))
        second_run.refresh_from_db()
        assert second_run.imported_issues == 0
        assert second_run.skipped_issues == 1

    def test_mix_of_new_and_already_linked_issues(self, project, states, linked_repo):
        first_run = GithubBackfillRun.objects.create(project=project, linked_repo=linked_repo)
        client = make_client_mock(issues=[gh_issue(1)])
        with patch("plane.bgtasks.github_app.backfill.GithubAppClient", return_value=client):
            run_github_backfill(str(first_run.id))

        second_run = GithubBackfillRun.objects.create(project=project, linked_repo=linked_repo)
        client = make_client_mock(issues=[gh_issue(1), gh_issue(2)])
        with patch("plane.bgtasks.github_app.backfill.GithubAppClient", return_value=client):
            run_github_backfill(str(second_run.id))

        second_run.refresh_from_db()
        assert second_run.imported_issues == 1
        assert second_run.skipped_issues == 1


@pytest.mark.unit
@pytest.mark.django_db
class TestRunGithubBackfillClosedToggle:
    def test_closed_issues_excluded_by_default(self, project, states, linked_repo):
        run = GithubBackfillRun.objects.create(project=project, linked_repo=linked_repo, include_closed_issues=False)
        client = make_client_mock(issues=[gh_issue(1, state="closed")])
        with patch("plane.bgtasks.github_app.backfill.GithubAppClient", return_value=client):
            run_github_backfill(str(run.id))

        client.list_repo_issues.assert_called_once_with("acme/widgets", state="open")

    def test_include_closed_issues_moves_to_mapped_closed_state(self, project, states, linked_repo):
        GithubProjectStateMapping.objects.create(project=project, issue_closed_state=states["done"])
        run = GithubBackfillRun.objects.create(project=project, linked_repo=linked_repo, include_closed_issues=True)
        client = make_client_mock(issues=[gh_issue(1, state="closed")])
        with patch("plane.bgtasks.github_app.backfill.GithubAppClient", return_value=client):
            run_github_backfill(str(run.id))

        client.list_repo_issues.assert_called_once_with("acme/widgets", state="all")
        issue = Issue.objects.get(project=project)
        assert issue.state_id == states["done"].id

    def test_closed_issue_without_mapping_falls_back_to_project_default_state(self, project, states, linked_repo):
        # "Backlog" is the state.default=True state, so newly created issues start
        # there; point project.default_state at "Done" instead so a successful
        # fallback move is observable.
        project.default_state = states["done"]
        project.save(update_fields=["default_state"])
        run = GithubBackfillRun.objects.create(project=project, linked_repo=linked_repo, include_closed_issues=True)
        client = make_client_mock(issues=[gh_issue(1, state="closed")])
        with patch("plane.bgtasks.github_app.backfill.GithubAppClient", return_value=client):
            run_github_backfill(str(run.id))

        issue = Issue.objects.get(project=project)
        assert issue.state_id == states["done"].id


@pytest.mark.unit
@pytest.mark.django_db
class TestPullRequestLinking:
    def test_links_pr_by_identifier_in_title(self, project, states, linked_repo):
        issue = Issue.objects.create(project=project, name="Bug", state=states["backlog"])
        GithubIssueLink.objects.create(
            project=project,
            issue=issue,
            linked_repo=linked_repo,
            gh_issue_id=1,
            gh_issue_number=1,
            url="https://github.com/acme/widgets/issues/1",
            gh_state="open",
            gh_updated_at=timezone.now(),
        )
        pr = gh_pr(5, title=f"Fix {project.identifier}-{issue.sequence_id}", state="open")

        linked = _link_pull_request(linked_repo, project, pr, {}, UserFactory(), None)

        assert linked is True
        assert GithubPullRequestLink.objects.filter(issue=issue, pr_id=pr["id"]).exists()

    def test_links_pr_by_closing_keyword_to_imported_issue(self, project, states, linked_repo):
        issue = Issue.objects.create(project=project, name="Bug", state=states["backlog"])
        pr = gh_pr(5, body="fixes #1", state="open")

        linked = _link_pull_request(linked_repo, project, pr, {1: issue}, UserFactory(), None)

        assert linked is True
        assert GithubPullRequestLink.objects.filter(issue=issue, pr_id=pr["id"]).exists()

    def test_unreferenced_pr_is_not_linked(self, project, states, linked_repo):
        pr = gh_pr(5, title="Unrelated change", state="open")

        linked = _link_pull_request(linked_repo, project, pr, {}, UserFactory(), None)

        assert linked is False
        assert not GithubPullRequestLink.objects.filter(pr_id=pr["id"]).exists()

    def test_merged_pr_moves_state_and_relink_never_regresses(self, project, states, linked_repo):
        opened_state = State.objects.create(project=project, name="In Review", color="#000", group="started")
        mapping = GithubProjectStateMapping.objects.create(
            project=project, pr_opened_state=opened_state, pr_merged_state=states["done"]
        )
        issue = Issue.objects.create(project=project, name="Bug", state=states["backlog"])
        bot_user = UserFactory()

        open_pr = gh_pr(5, body="fixes #1", state="open")
        _link_pull_request(linked_repo, project, open_pr, {1: issue}, bot_user, mapping)
        issue.refresh_from_db()
        assert issue.state_id == opened_state.id

        merged_pr = gh_pr(5, body="fixes #1", state="closed", merged_at="2024-01-02T00:00:00Z")
        _link_pull_request(linked_repo, project, merged_pr, {1: issue}, bot_user, mapping)
        issue.refresh_from_db()
        assert issue.state_id == states["done"].id

        # Re-running the backfill (GitHub still reports the PR as merged) must not
        # regress the link or double-record the "merged" activity.
        _link_pull_request(linked_repo, project, merged_pr, {1: issue}, bot_user, mapping)
        assert GithubPullRequestLink.objects.filter(issue=issue, pr_id=open_pr["id"]).count() == 1
        link = GithubPullRequestLink.objects.get(issue=issue, pr_id=open_pr["id"])
        assert link.state == "merged"
        assert IssueActivity.objects.filter(issue=issue, comment__icontains="merged pull request").count() == 1


@pytest.mark.unit
@pytest.mark.django_db
class TestLabelAndAssigneeMatching:
    def test_matches_existing_label_case_insensitively_and_creates_missing(self, project):
        Label.objects.create(project=project, workspace=project.workspace, name="Bug", color="#f00")

        labels = match_or_create_labels(project, ["bug", "new-label"])

        assert {label.name for label in labels} == {"Bug", "new-label"}
        assert Label.objects.filter(project=project).count() == 2

    def test_assignee_matches_only_project_members_with_linked_github_account(self, project):
        member = UserFactory()
        ProjectMember.objects.create(project=project, member=member, workspace=project.workspace, role=15)
        Account.objects.create(user=member, provider="github", provider_account_id="4242")
        outsider = UserFactory()
        Account.objects.create(user=outsider, provider="github", provider_account_id="9999")

        mapped, unmapped = map_assignees(project, [{"id": 4242, "login": "member"}, {"id": 9999, "login": "outsider"}])

        assert mapped == {"member": member}
        assert unmapped == ["outsider"]


@pytest.mark.unit
@pytest.mark.django_db
class TestOneActiveRunPerRepo:
    def test_second_active_run_for_same_repo_is_rejected(self, project, linked_repo):
        GithubBackfillRun.objects.create(project=project, linked_repo=linked_repo, status="running")
        with pytest.raises(IntegrityError), transaction.atomic():
            GithubBackfillRun.objects.create(project=project, linked_repo=linked_repo, status="queued")

    def test_new_run_allowed_once_previous_run_completed(self, project, linked_repo):
        first = GithubBackfillRun.objects.create(project=project, linked_repo=linked_repo, status="completed")
        second = GithubBackfillRun.objects.create(project=project, linked_repo=linked_repo, status="queued")
        assert first.id != second.id


@pytest.mark.unit
@pytest.mark.django_db
class TestRunGithubBackfillFailureHandling:
    def test_failed_run_records_status_and_error(self, project, states, linked_repo):
        run = GithubBackfillRun.objects.create(project=project, linked_repo=linked_repo)
        client = Mock()
        client.list_repo_issues.side_effect = RuntimeError("boom")
        with patch("plane.bgtasks.github_app.backfill.GithubAppClient", return_value=client):
            run_github_backfill(str(run.id))

        run.refresh_from_db()
        assert run.status == "failed"
        assert "boom" in run.error

    def test_non_queued_run_is_not_reprocessed(self, project, linked_repo):
        run = GithubBackfillRun.objects.create(project=project, linked_repo=linked_repo, status="completed")
        client = make_client_mock()
        with patch("plane.bgtasks.github_app.backfill.GithubAppClient", return_value=client):
            run_github_backfill(str(run.id))

        client.list_repo_issues.assert_not_called()
