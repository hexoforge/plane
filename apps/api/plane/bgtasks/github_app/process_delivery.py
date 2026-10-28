# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from celery import shared_task
from django.utils import timezone

from plane.db.models import GithubWebhookDelivery
from plane.utils.exception_logger import log_exception

from .handlers import (
    handle_installation,
    handle_installation_repositories,
    handle_issue_comment,
    handle_issues,
    handle_pull_request,
)

EVENT_HANDLERS = {
    "pull_request": handle_pull_request,
    "issues": handle_issues,
    "issue_comment": handle_issue_comment,
    "installation": handle_installation,
    "installation_repositories": handle_installation_repositories,
}


@shared_task
def process_github_delivery(delivery_id):
    try:
        delivery = GithubWebhookDelivery.objects.get(id=delivery_id)
    except GithubWebhookDelivery.DoesNotExist:
        return

    handler = EVENT_HANDLERS.get(delivery.event)
    if not handler:
        delivery.status = "skipped"
        delivery.processed_at = timezone.now()
        delivery.save(update_fields=["status", "processed_at"])
        return

    try:
        delivery.status = handler(delivery.payload)
    except Exception as e:
        log_exception(e)
        delivery.status = "failed"
        delivery.error = str(e)

    delivery.processed_at = timezone.now()
    delivery.save(update_fields=["status", "processed_at", "error"])
