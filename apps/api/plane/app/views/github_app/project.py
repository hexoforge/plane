# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from datetime import timedelta

from django.db import IntegrityError
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response

from plane.app.permissions import ROLE, allow_permission
from plane.app.serializers import (
    GithubBackfillRunSerializer,
    GithubLinkedRepositorySerializer,
    GithubProjectStateMappingSerializer,
)
from plane.bgtasks.github_app.backfill import run_github_backfill
from plane.db.models import (
    GithubAppInstallation,
    GithubBackfillRun,
    GithubLinkedRepository,
    GithubProjectStateMapping,
    Project,
    State,
)
from plane.utils.exception_logger import log_exception

from ..base import BaseAPIView
from .base import require_github_app

# A run whose heartbeat (updated_at, touched on every page/issue/PR processed) is
# older than this is assumed to belong to a dead worker and is failed so a new run
# can start.
STALE_BACKFILL_RUN_THRESHOLD = timedelta(minutes=30)


class GithubProjectRepositoriesEndpoint(BaseAPIView):
    @allow_permission(allowed_roles=[ROLE.ADMIN, ROLE.MEMBER], level="PROJECT")
    def get(self, request, slug, project_id):
        repos = GithubLinkedRepository.objects.filter(project_id=project_id, workspace__slug=slug)
        serializer = GithubLinkedRepositorySerializer(repos, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @allow_permission(allowed_roles=[ROLE.ADMIN], level="PROJECT")
    @require_github_app
    def post(self, request, slug, project_id):
        project = Project.objects.get(id=project_id, workspace__slug=slug)
        installation = GithubAppInstallation.objects.filter(workspace=project.workspace).first()
        if not installation:
            return Response({"error": "no installation"}, status=status.HTTP_400_BAD_REQUEST)

        repo_id = request.data.get("repo_id")
        if not repo_id:
            return Response({"error": "repo_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            linked_repo = GithubLinkedRepository.objects.create(
                project=project,
                installation=installation,
                repo_id=repo_id,
                full_name=request.data.get("full_name", ""),
                private=request.data.get("private", False),
                default_branch=request.data.get("default_branch", "main"),
                html_url=request.data.get("html_url", ""),
            )
        except IntegrityError:
            return Response({"error": "repository already linked"}, status=status.HTTP_409_CONFLICT)

        serializer = GithubLinkedRepositorySerializer(linked_repo)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @allow_permission(allowed_roles=[ROLE.ADMIN], level="PROJECT")
    def delete(self, request, slug, project_id, pk):
        linked_repo = GithubLinkedRepository.objects.get(pk=pk, project_id=project_id, workspace__slug=slug)
        linked_repo.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class GithubProjectRepositoryBackfillEndpoint(BaseAPIView):
    @allow_permission(allowed_roles=[ROLE.ADMIN], level="PROJECT")
    def get(self, request, slug, project_id, pk):
        linked_repo = GithubLinkedRepository.objects.get(pk=pk, project_id=project_id, workspace__slug=slug)
        run = GithubBackfillRun.objects.filter(linked_repo=linked_repo).first()
        if not run:
            return Response(None, status=status.HTTP_200_OK)
        return Response(GithubBackfillRunSerializer(run).data, status=status.HTTP_200_OK)

    @allow_permission(allowed_roles=[ROLE.ADMIN], level="PROJECT")
    @require_github_app
    def post(self, request, slug, project_id, pk):
        linked_repo = GithubLinkedRepository.objects.get(pk=pk, project_id=project_id, workspace__slug=slug)

        now = timezone.now()
        stale_cutoff = now - STALE_BACKFILL_RUN_THRESHOLD
        GithubBackfillRun.objects.filter(
            linked_repo=linked_repo, status__in=["queued", "running"], updated_at__lt=stale_cutoff
        ).update(
            status="failed",
            error="Backfill run timed out (worker stopped responding)",
            completed_at=now,
            updated_at=now,
        )

        try:
            run = GithubBackfillRun.objects.create(
                project=linked_repo.project,
                linked_repo=linked_repo,
                initiated_by=request.user,
                include_closed_issues=bool(request.data.get("include_closed_issues", False)),
            )
        except IntegrityError:
            return Response(
                {"error": "A backfill is already running for this repository"}, status=status.HTTP_409_CONFLICT
            )

        try:
            run_github_backfill.delay(str(run.id))
        except Exception as e:
            log_exception(e)
            run.status = "failed"
            run.error = f"Failed to queue backfill: {e}"[:2000]
            run.completed_at = timezone.now()
            run.save(update_fields=["status", "error", "completed_at", "updated_at"])
            return Response(
                {"error": "Failed to queue the backfill. Please try again."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(GithubBackfillRunSerializer(run).data, status=status.HTTP_201_CREATED)


class GithubProjectStateMappingEndpoint(BaseAPIView):
    @allow_permission(allowed_roles=[ROLE.ADMIN, ROLE.MEMBER], level="PROJECT")
    def get(self, request, slug, project_id):
        project = Project.objects.get(id=project_id, workspace__slug=slug)
        mapping, _ = GithubProjectStateMapping.objects.get_or_create(project=project)
        serializer = GithubProjectStateMappingSerializer(mapping)
        return Response(serializer.data, status=status.HTTP_200_OK)

    STATE_FIELDS = ["pr_opened_state", "pr_merged_state", "issue_closed_state", "issue_reopened_state"]

    @allow_permission(allowed_roles=[ROLE.ADMIN], level="PROJECT")
    def put(self, request, slug, project_id):
        project = Project.objects.get(id=project_id, workspace__slug=slug)

        for field in self.STATE_FIELDS:
            state_id = request.data.get(field)
            if state_id and not State.objects.filter(id=state_id, project=project).exists():
                return Response({field: "Invalid state for this project"}, status=status.HTTP_400_BAD_REQUEST)

        mapping, _ = GithubProjectStateMapping.objects.get_or_create(project=project)
        serializer = GithubProjectStateMappingSerializer(mapping, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
