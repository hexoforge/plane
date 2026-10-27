# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from unittest import mock

import pytest
from django.core.mail import EmailMultiAlternatives, get_connection

from plane.utils.resend_email import RESEND_API_URL, ResendEmailBackend


def _message(connection):
    msg = EmailMultiAlternatives(
        subject="Hi",
        body="plain",
        from_email="Plane <plane@example.com>",
        to=["a@example.com"],
        cc=["c@example.com"],
        connection=connection,
    )
    msg.attach_alternative("<p>html</p>", "text/html")
    msg.attach("report.csv", "a,b\n1,2", "text/csv")
    return msg


@pytest.mark.unit
def test_send_posts_payload_to_resend():
    backend = ResendEmailBackend(api_key="test-key", host="smtp.example.com", port=587)
    with mock.patch("plane.utils.resend_email.requests.post") as post:
        post.return_value.json.return_value = {"id": "abc"}
        assert _message(backend).send() == 1
    url = post.call_args.args[0]
    kwargs = post.call_args.kwargs
    assert url == RESEND_API_URL
    assert kwargs["headers"]["Authorization"] == "Bearer test-key"
    payload = kwargs["json"]
    assert payload["from"] == "Plane <plane@example.com>"
    assert payload["to"] == ["a@example.com"]
    assert payload["cc"] == ["c@example.com"]
    assert payload["text"] == "plain"
    assert payload["html"] == "<p>html</p>"
    assert payload["attachments"][0]["filename"] == "report.csv"


@pytest.mark.unit
def test_errors_raise_unless_fail_silently():
    with mock.patch("plane.utils.resend_email.requests.post", side_effect=RuntimeError("boom")):
        with pytest.raises(RuntimeError):
            _message(ResendEmailBackend(api_key="k")).send()
        assert _message(ResendEmailBackend(api_key="k", fail_silently=True)).send() == 0


@pytest.mark.unit
def test_get_connection_uses_resend_when_configured(settings):
    settings.EMAIL_BACKEND = "plane.utils.resend_email.ResendEmailBackend"
    settings.RESEND_API_KEY = "k"
    assert isinstance(get_connection(host="h", port=1, use_tls=True), ResendEmailBackend)
