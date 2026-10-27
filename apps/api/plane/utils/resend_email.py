# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import base64
import logging

import requests
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger("plane.worker")

RESEND_API_URL = "https://api.resend.com/emails"


class ResendEmailBackend(BaseEmailBackend):
    """Sends mail through the Resend HTTP API. SMTP kwargs passed by callers are ignored."""

    def __init__(self, fail_silently=False, api_key=None, timeout=None, **kwargs):
        super().__init__(fail_silently=fail_silently)
        self.api_key = api_key or settings.RESEND_API_KEY
        self.timeout = timeout or 30

    def _payload(self, message):
        payload = {
            "from": message.from_email,
            "to": list(message.to),
            "subject": message.subject,
        }
        if message.cc:
            payload["cc"] = list(message.cc)
        if message.bcc:
            payload["bcc"] = list(message.bcc)
        if message.reply_to:
            payload["reply_to"] = list(message.reply_to)
        if message.content_subtype == "html":
            payload["html"] = message.body
        else:
            payload["text"] = message.body
        for content, mimetype in getattr(message, "alternatives", []) or []:
            if mimetype == "text/html":
                payload["html"] = content
        attachments = []
        for attachment in message.attachments:
            if isinstance(attachment, tuple):
                filename, content, _ = attachment
            else:
                filename, content = attachment.get_filename(), attachment.get_payload(decode=True)
            if isinstance(content, str):
                content = content.encode()
            attachments.append({"filename": filename, "content": base64.b64encode(content).decode()})
        if attachments:
            payload["attachments"] = attachments
        return payload

    def send_messages(self, email_messages):
        sent = 0
        for message in email_messages or []:
            if not message.recipients():
                continue
            try:
                response = requests.post(
                    RESEND_API_URL,
                    json=self._payload(message),
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=self.timeout,
                )
                response.raise_for_status()
                logger.info("Resend accepted email id=%s", response.json().get("id"))
                sent += 1
            except Exception:
                if not self.fail_silently:
                    raise
        return sent
