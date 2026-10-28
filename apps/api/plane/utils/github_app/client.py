# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# shortcut: stub only; the outbound part (feat/github-outbound) implements App JWT
# auth, installation token caching and retries. Replace this file wholesale when
# merging that part in rather than reconciling the two.


class GithubAppClient:
    """Thin client for calls to the GitHub App API.

    Real implementation (JWT signing, installation token caching/refresh,
    rate limit handling) lives in the outbound integration part. Inbound
    code only needs to construct this and call the methods below.
    """

    def get_installation(self, installation_id: int) -> dict:
        raise NotImplementedError

    def list_installation_repos(self, installation_id: int) -> list[dict]:
        raise NotImplementedError
