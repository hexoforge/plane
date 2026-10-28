# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import pytest

from plane.bgtasks.github_app.handlers import handle_installation, handle_installation_repositories
from plane.db.models import GithubAppInstallation


@pytest.mark.unit
@pytest.mark.django_db
class TestHandleInstallation:
    def test_deleted_soft_deletes_and_deactivates_repos(self, installation, linked_repo):
        result = handle_installation({"action": "deleted", "installation": {"id": installation.installation_id}})
        assert result == "processed"
        assert not GithubAppInstallation.objects.filter(id=installation.id).exists()
        assert GithubAppInstallation.all_objects.get(id=installation.id).deleted_at is not None
        linked_repo.refresh_from_db()
        assert linked_repo.is_active is False

    def test_suspend_sets_suspended_at(self, installation):
        handle_installation({"action": "suspend", "installation": {"id": installation.installation_id}})
        installation.refresh_from_db()
        assert installation.suspended_at is not None

    def test_unsuspend_clears_suspended_at(self, installation):
        handle_installation({"action": "suspend", "installation": {"id": installation.installation_id}})
        handle_installation({"action": "unsuspend", "installation": {"id": installation.installation_id}})
        installation.refresh_from_db()
        assert installation.suspended_at is None

    def test_unknown_installation_is_skipped(self):
        result = handle_installation({"action": "deleted", "installation": {"id": 999999999}})
        assert result == "skipped"


@pytest.mark.unit
@pytest.mark.django_db
class TestHandleInstallationRepositories:
    def test_removed_deactivates_linked_repo(self, installation, linked_repo):
        result = handle_installation_repositories(
            {
                "action": "removed",
                "installation": {"id": installation.installation_id},
                "repositories_removed": [{"id": linked_repo.repo_id, "full_name": linked_repo.full_name}],
            }
        )
        assert result == "processed"
        linked_repo.refresh_from_db()
        assert linked_repo.is_active is False

    def test_added_action_is_skipped(self, installation, linked_repo):
        result = handle_installation_repositories(
            {
                "action": "added",
                "installation": {"id": installation.installation_id},
                "repositories_added": [{"id": linked_repo.repo_id}],
            }
        )
        assert result == "skipped"
