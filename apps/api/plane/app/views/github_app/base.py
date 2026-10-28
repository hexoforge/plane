# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from functools import wraps

from django.conf import settings
from django.core import signing
from rest_framework import status
from rest_framework.response import Response

GITHUB_SETUP_STATE_SALT = "plane.github-app.setup"
GITHUB_SETUP_STATE_MAX_AGE = 60 * 60


def is_github_app_configured() -> bool:
    return bool(
        settings.GITHUB_APP_ID
        and settings.GITHUB_APP_PRIVATE_KEY
        and settings.GITHUB_APP_WEBHOOK_SECRET
        and settings.GITHUB_APP_SLUG
    )


def require_github_app(view_func):
    """Return 400 instead of calling the view when the GitHub App isn't configured."""

    @wraps(view_func)
    def wrapper(self, request, *args, **kwargs):
        if not is_github_app_configured():
            return Response({"error": "not configured"}, status=status.HTTP_400_BAD_REQUEST)
        return view_func(self, request, *args, **kwargs)

    return wrapper


def sign_setup_state(workspace_slug: str, user_id) -> str:
    return signing.dumps({"workspace_slug": workspace_slug, "user_id": str(user_id)}, salt=GITHUB_SETUP_STATE_SALT)


def unsign_setup_state(state: str) -> dict:
    """Raises django.core.signing.BadSignature (incl. SignatureExpired) on failure."""
    return signing.loads(state, salt=GITHUB_SETUP_STATE_SALT, max_age=GITHUB_SETUP_STATE_MAX_AGE)
