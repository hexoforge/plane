# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import hashlib
import hmac


def verify_signature(payload_body: bytes, signature_header: str | None, secret: str) -> bool:
    """Verify the X-Hub-Signature-256 header for a GitHub webhook delivery.

    Compares in constant time against an HMAC-SHA256 digest of the raw
    request body, since the body must be hashed exactly as GitHub sent it
    (before any JSON parsing/re-serialization).
    """
    if not signature_header or not signature_header.startswith("sha256="):
        return False

    expected = hmac.new(secret.encode("utf-8"), payload_body, hashlib.sha256).hexdigest()
    received = signature_header[len("sha256=") :]
    return hmac.compare_digest(expected, received)
