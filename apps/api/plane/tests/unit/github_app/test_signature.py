# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import hashlib
import hmac

import pytest

from plane.utils.github_app.signature import verify_signature


@pytest.mark.unit
class TestVerifySignature:
    def _sign(self, body, secret):
        return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

    def test_valid_signature(self):
        body = b'{"hello":"world"}'
        secret = "s3cret"
        assert verify_signature(body, self._sign(body, secret), secret) is True

    def test_invalid_signature(self):
        body = b'{"hello":"world"}'
        assert verify_signature(body, self._sign(body, "other-secret"), "s3cret") is False

    def test_tampered_body(self):
        secret = "s3cret"
        signature = self._sign(b'{"hello":"world"}', secret)
        assert verify_signature(b'{"hello":"mallory"}', signature, secret) is False

    def test_missing_signature(self):
        assert verify_signature(b"{}", None, "s3cret") is False
        assert verify_signature(b"{}", "", "s3cret") is False

    def test_malformed_signature_prefix(self):
        assert verify_signature(b"{}", "sha1=deadbeef", "s3cret") is False
