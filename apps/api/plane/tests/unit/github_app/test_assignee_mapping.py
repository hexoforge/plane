# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from unittest.mock import Mock

import pytest

from plane.db.models import Account
from plane.tests.factories import ProjectFactory, ProjectMemberFactory, UserFactory
from plane.utils.github_app.assignee_mapping import map_assignees


@pytest.mark.unit
@pytest.mark.django_db
class TestMapAssignees:
    def test_maps_by_linked_github_account(self):
        project = ProjectFactory()
        member = UserFactory()
        ProjectMemberFactory(project=project, member=member, role=15)
        Account.objects.create(user=member, provider="github", provider_account_id="111")

        mapped, unmapped = map_assignees(project, [{"id": 111, "login": "member"}])

        assert mapped == {"member": member}
        assert unmapped == []

    def test_unknown_login_is_unmapped(self):
        project = ProjectFactory()

        mapped, unmapped = map_assignees(project, [{"id": 999, "login": "stranger"}])

        assert mapped == {}
        assert unmapped == ["stranger"]

    def test_user_who_left_the_project_is_unmapped(self):
        project = ProjectFactory()
        member = UserFactory()
        ProjectMemberFactory(project=project, member=member, role=15, is_active=False)
        Account.objects.create(user=member, provider="github", provider_account_id="111")

        mapped, unmapped = map_assignees(project, [{"id": 111, "login": "member"}])

        assert mapped == {}
        assert unmapped == ["member"]

    def test_guest_role_member_is_unmapped(self):
        project = ProjectFactory()
        guest = UserFactory()
        ProjectMemberFactory(project=project, member=guest, role=5)
        Account.objects.create(user=guest, provider="github", provider_account_id="111")

        mapped, unmapped = map_assignees(project, [{"id": 111, "login": "guest"}])

        assert mapped == {}
        assert unmapped == ["guest"]

    def test_maps_by_verified_email_when_no_linked_account(self):
        project = ProjectFactory()
        member = UserFactory(email="octocat@example.com")
        ProjectMemberFactory(project=project, member=member, role=15)
        client = Mock()
        client.get_user.return_value = {"login": "octocat", "email": "octocat@example.com"}

        mapped, unmapped = map_assignees(project, [{"id": 222, "login": "octocat"}], client=client)

        assert mapped == {"octocat": member}
        assert unmapped == []
        client.get_user.assert_called_once_with("octocat")

    def test_github_user_with_no_public_email_is_unmapped(self):
        project = ProjectFactory()
        client = Mock()
        client.get_user.return_value = {"login": "octocat", "email": None}

        mapped, unmapped = map_assignees(project, [{"id": 222, "login": "octocat"}], client=client)

        assert mapped == {}
        assert unmapped == ["octocat"]

    def test_ambiguous_email_match_is_unmapped(self, monkeypatch):
        # Plane's User.email is DB-unique, so two real rows can't share one
        # exactly - but case-insensitive lookups can still surface more than
        # one row (e.g. differing only by case), which must stay unmapped
        # rather than guessing.
        project = ProjectFactory()
        first = UserFactory()
        second = UserFactory()
        ProjectMemberFactory(project=project, member=first, role=15)
        ProjectMemberFactory(project=project, member=second, role=15)
        client = Mock()
        client.get_user.return_value = {"login": "octocat", "email": "octocat@example.com"}

        import plane.utils.github_app.assignee_mapping as assignee_mapping_module

        monkeypatch.setattr(
            assignee_mapping_module.User.objects, "filter", lambda **kwargs: [first, second]
        )

        mapped, unmapped = map_assignees(project, [{"id": 222, "login": "octocat"}], client=client)

        assert mapped == {}
        assert unmapped == ["octocat"]

    def test_no_client_skips_email_lookup(self):
        project = ProjectFactory()
        member = UserFactory(email="octocat@example.com")
        ProjectMemberFactory(project=project, member=member, role=15)

        mapped, unmapped = map_assignees(project, [{"id": 222, "login": "octocat"}], client=None)

        assert mapped == {}
        assert unmapped == ["octocat"]

    def test_multiple_assignees(self):
        project = ProjectFactory()
        first = UserFactory()
        second = UserFactory()
        ProjectMemberFactory(project=project, member=first, role=15)
        ProjectMemberFactory(project=project, member=second, role=15)
        Account.objects.create(user=first, provider="github", provider_account_id="1")
        Account.objects.create(user=second, provider="github", provider_account_id="2")

        mapped, unmapped = map_assignees(
            project,
            [
                {"id": 1, "login": "first"},
                {"id": 2, "login": "second"},
                {"id": 3, "login": "stranger"},
            ],
        )

        assert mapped == {"first": first, "second": second}
        assert unmapped == ["stranger"]

    def test_cache_is_reused_across_calls(self):
        project = ProjectFactory()
        member = UserFactory(email="octocat@example.com")
        ProjectMemberFactory(project=project, member=member, role=15)
        client = Mock()
        client.get_user.return_value = {"login": "octocat", "email": "octocat@example.com"}
        cache = {}

        map_assignees(project, [{"id": 222, "login": "octocat"}], client=client, cache=cache)
        map_assignees(project, [{"id": 222, "login": "octocat"}], client=client, cache=cache)

        client.get_user.assert_called_once_with("octocat")

    def test_assignee_without_login_is_ignored(self):
        project = ProjectFactory()

        mapped, unmapped = map_assignees(project, [{"id": 1}])

        assert mapped == {}
        assert unmapped == []
