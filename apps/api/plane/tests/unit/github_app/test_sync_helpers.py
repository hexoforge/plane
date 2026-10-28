# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import pytest

from plane.bgtasks.github_app.sync import get_or_create_bot_user, upsert_installation
from plane.db.models import GithubAppInstallation


@pytest.mark.unit
@pytest.mark.django_db
class TestUpsertInstallation:
    def test_creates_new_installation(self, workspace, create_user):
        installation = upsert_installation(
            workspace,
            create_user,
            installation_id=111,
            account_login="acme",
            account_type="Organization",
            target_id=1,
        )
        assert installation.installation_id == 111
        assert GithubAppInstallation.objects.filter(workspace=workspace).count() == 1

    def test_reconnect_revives_soft_deleted_row_for_same_installation_id(self, workspace, create_user):
        installation = upsert_installation(
            workspace, create_user, installation_id=111, account_login="acme", account_type="Organization", target_id=1
        )
        installation.delete()
        assert GithubAppInstallation.objects.filter(workspace=workspace).count() == 0

        revived = upsert_installation(
            workspace, create_user, installation_id=111, account_login="acme", account_type="Organization", target_id=1
        )
        assert revived.id == installation.id
        assert revived.deleted_at is None

    def test_switching_installation_retires_previous_active_row(self, workspace, create_user):
        first = upsert_installation(
            workspace, create_user, installation_id=111, account_login="acme", account_type="Organization", target_id=1
        )
        second = upsert_installation(
            workspace, create_user, installation_id=222, account_login="acme2", account_type="Organization", target_id=2
        )
        assert GithubAppInstallation.objects.filter(workspace=workspace).count() == 1
        assert GithubAppInstallation.objects.get(workspace=workspace).id == second.id
        assert GithubAppInstallation.all_objects.get(id=first.id).deleted_at is not None


@pytest.mark.unit
@pytest.mark.django_db
class TestGetOrCreateBotUser:
    def test_creates_bot_user_once(self, workspace):
        bot1 = get_or_create_bot_user(workspace)
        bot2 = get_or_create_bot_user(workspace)
        assert bot1.id == bot2.id
        assert bot1.is_bot is True
