# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from plane.db.models import Account, ProjectMember, User


def map_assignees(project, gh_assignees, client=None, cache=None):
    """Map GitHub assignees to active Plane project members.

    Matches, in order: (a) a Plane user's linked GitHub account (by GitHub
    numeric user id, which is what GitHub OAuth stores and what webhook/API
    payloads also carry), (b) the GitHub user's public/verified email matching
    exactly one Plane user's email. Anything else (unknown login, user left
    the project, ambiguous email) is unmapped. `client`, if given, is used to
    look up a GitHub user's public email for strategy (b); omit it to only use
    strategy (a) (e.g. when no network call should be made).

    `cache` is an optional dict the caller can reuse across many issues in one
    run (backfill) so the same login is only resolved once.

    Returns (mapped: dict[login, User], unmapped_logins: list[str]).
    """
    cache = {} if cache is None else cache
    member_user_ids = set(
        ProjectMember.objects.filter(project=project, is_active=True, role__gte=15).values_list(
            "member_id", flat=True
        )
    )

    mapped = {}
    unmapped_logins = []
    for assignee in gh_assignees:
        login = assignee.get("login")
        if not login:
            continue

        if login in cache:
            user = cache[login]
        else:
            user = _match_by_account(assignee.get("id"), member_user_ids) or _match_by_email(
                login, member_user_ids, client
            )
            cache[login] = user

        if user:
            mapped[login] = user
        else:
            unmapped_logins.append(login)

    return mapped, unmapped_logins


def _match_by_account(gh_id, member_user_ids):
    if gh_id is None:
        return None
    account = (
        Account.objects.filter(provider="github", provider_account_id=str(gh_id), user_id__in=member_user_ids)
        .select_related("user")
        .first()
    )
    return account.user if account else None


def _match_by_email(login, member_user_ids, client):
    if not client:
        return None
    try:
        gh_user = client.get_user(login)
    except Exception:
        return None

    email = (gh_user or {}).get("email")
    if not email:
        return None

    users = list(User.objects.filter(email__iexact=email, id__in=member_user_ids))
    return users[0] if len(users) == 1 else None
