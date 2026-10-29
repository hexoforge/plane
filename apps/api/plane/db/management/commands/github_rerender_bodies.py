# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.core.management.base import BaseCommand

from plane.db.models import GithubCommentLink, GithubIssueLink, IssueActivity
from plane.utils.github_app.client import GithubAppClient
from plane.utils.github_app.markdown import render_markdown


class Command(BaseCommand):
    help = (
        "Re-render already-imported GitHub issue/comment bodies with the current "
        "markdown renderer. Refetches the raw markdown from GitHub when possible; "
        "otherwise falls back to the item's stored plain text (description_stripped / "
        "comment_stripped), which approximates the original markdown for bodies "
        "imported before this renderer existed (fenced code block language and some "
        "formatting may be lost in that fallback). Idempotent: an item whose "
        "re-rendered HTML is unchanged is left alone. An issue with a 'description' "
        "IssueActivity is skipped, since GitHub-sourced edits never create one (only "
        "a human editing it in Plane does) - overwriting it would discard that edit."
    )

    def add_arguments(self, parser):
        parser.add_argument("--workspace", default=None, help="Workspace slug to limit to")
        parser.add_argument("--project", default=None, help="Project id to limit to")
        parser.add_argument("--dry-run", action="store_true", default=False)

    def handle(self, *args, **options):
        workspace_slug = options.get("workspace")
        project_id = options.get("project")
        dry_run = options.get("dry_run")

        issue_stats = self._rerender_issues(workspace_slug, project_id, dry_run)
        comment_stats = self._rerender_comments(workspace_slug, project_id, dry_run)

        self.stdout.write(
            self.style.SUCCESS(
                "issues: rendered={rendered} unchanged={unchanged} "
                "skipped_edited_in_plane={skipped_edited} errors={errors}; "
                "comments: rendered={c_rendered} unchanged={c_unchanged} errors={c_errors}".format(
                    **issue_stats,
                    c_rendered=comment_stats["rendered"],
                    c_unchanged=comment_stats["unchanged"],
                    c_errors=comment_stats["errors"],
                )
            )
        )

    def _rerender_issues(self, workspace_slug, project_id, dry_run):
        links = GithubIssueLink.objects.select_related("issue", "linked_repo", "linked_repo__installation")
        if workspace_slug:
            links = links.filter(workspace__slug=workspace_slug)
        if project_id:
            links = links.filter(project_id=project_id)

        stats = {"rendered": 0, "unchanged": 0, "skipped_edited": 0, "errors": 0}
        edited_issue_ids = set(
            IssueActivity.objects.filter(
                issue_id__in=links.values_list("issue_id", flat=True), field="description"
            ).values_list("issue_id", flat=True)
        )

        for link in links.iterator():
            issue = link.issue
            if issue.id in edited_issue_ids:
                stats["skipped_edited"] += 1
                continue

            try:
                body = self._issue_source_markdown(link)
            except Exception as e:
                stats["errors"] += 1
                self.stderr.write(f"issue {link.linked_repo.full_name}#{link.gh_issue_number}: {e}")
                continue

            new_html = render_markdown(body)
            if new_html == issue.description_html:
                stats["unchanged"] += 1
                continue

            stats["rendered"] += 1
            if not dry_run:
                issue.description_html = new_html
                issue.description_binary = None
                issue.save(
                    update_fields=["description_html", "description_stripped", "description_binary", "updated_at"]
                )

        return stats

    def _issue_source_markdown(self, link):
        try:
            client = GithubAppClient(link.linked_repo.installation.installation_id)
            gh_issue = client.get_issue(link.linked_repo.full_name, link.gh_issue_number)
            return gh_issue.get("body") or ""
        except Exception:
            return link.issue.description_stripped or ""

    def _rerender_comments(self, workspace_slug, project_id, dry_run):
        links = GithubCommentLink.objects.filter(source="github").select_related(
            "issue_comment", "issue_link", "issue_link__linked_repo", "issue_link__linked_repo__installation"
        )
        if workspace_slug:
            links = links.filter(workspace__slug=workspace_slug)
        if project_id:
            links = links.filter(issue_link__project_id=project_id)

        stats = {"rendered": 0, "unchanged": 0, "errors": 0}
        for link in links.iterator():
            comment = link.issue_comment
            try:
                body = self._comment_source_markdown(link)
            except Exception as e:
                stats["errors"] += 1
                self.stderr.write(f"comment {link.gh_comment_id}: {e}")
                continue

            new_html = render_markdown(body)
            if new_html == comment.comment_html:
                stats["unchanged"] += 1
                continue

            stats["rendered"] += 1
            if not dry_run:
                comment.comment_html = new_html
                comment.save(update_fields=["comment_html", "comment_stripped", "updated_at"])

        return stats

    def _comment_source_markdown(self, link):
        try:
            client = GithubAppClient(link.issue_link.linked_repo.installation.installation_id)
            gh_comment = client.get_issue_comment(link.issue_link.linked_repo.full_name, link.gh_comment_id)
            return gh_comment.get("body") or ""
        except Exception:
            return link.issue_comment.comment_stripped or ""
