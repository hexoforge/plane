/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { CircleAlert, ExternalLink, GitMerge, GitPullRequest, GitPullRequestDraft } from "lucide-react";
// plane imports
import { useTranslation } from "@plane/i18n";
import type {
  TGithubAssigneeLogin,
  TGithubPullRequestLink,
  TGithubPullRequestState,
  TWorkItemGithubLinks,
} from "@plane/types";
import { Avatar, Tooltip } from "@plane/ui";
import { cn } from "@plane/utils";

const PR_STATE_CONFIG: Record<TGithubPullRequestState, { className: string; icon: typeof GitPullRequest }> = {
  open: { className: "bg-green-50 text-success-primary", icon: GitPullRequest },
  draft: { className: "bg-layer-1 text-secondary", icon: GitPullRequestDraft },
  merged: { className: "bg-accent-subtle text-accent-primary", icon: GitMerge },
  closed: { className: "bg-red-50 text-danger-primary", icon: GitPullRequest },
};

type Props = {
  links: TWorkItemGithubLinks;
};

export function GithubCollapsibleContent(props: Props) {
  const { links } = props;
  // translation
  const { t } = useTranslation();

  return (
    <div className="flex flex-col gap-2 px-1.5 pb-2">
      {links.issue_link && (
        <>
          <a
            href={links.issue_link.url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center justify-between gap-2 rounded-md px-1.5 py-1.5 hover:bg-layer-1"
          >
            <span className="min-w-0 truncate text-body-sm-regular text-secondary">
              {t("github.linked_issue")}: {links.issue_link.repository_full_name}#{links.issue_link.gh_issue_number}
            </span>
            <span
              className={cn(
                "flex-shrink-0 rounded-sm px-2 py-0.5 text-11 font-medium",
                links.issue_link.gh_state === "open"
                  ? "bg-green-50 text-success-primary"
                  : "bg-red-50 text-danger-primary"
              )}
            >
              {links.issue_link.gh_state === "open" ? t("github.state.open") : t("github.state.closed")}
            </span>
          </a>
          {links.issue_link.assignee_logins.length > 0 && (
            <AssigneeLogins assignees={links.issue_link.assignee_logins} />
          )}
        </>
      )}
      {links.pull_requests.length > 0 && (
        <div className="flex max-h-64 flex-col gap-1.5 overflow-y-auto">
          {links.pull_requests.map((pr) => (
            <PullRequestCard key={pr.id} pullRequest={pr} />
          ))}
        </div>
      )}
    </div>
  );
}

function AssigneeLogins({ assignees }: { assignees: TGithubAssigneeLogin[] }) {
  const { t } = useTranslation();

  return (
    <div className="flex flex-wrap items-center gap-1.5 px-1.5 pb-1">
      <span className="text-body-xs-regular text-tertiary">{t("github.assignees")}:</span>
      {assignees.map((assignee) => (
        <span
          key={assignee.login}
          className={cn(
            "flex items-center gap-1 rounded-sm px-2 py-0.5 text-11 font-medium",
            assignee.mapped ? "bg-layer-1 text-secondary" : "bg-amber-50 text-amber-500"
          )}
        >
          {assignee.login}
          {!assignee.mapped && (
            <Tooltip tooltipContent={t("github.unmapped_assignee_tooltip")}>
              <CircleAlert className="size-3" aria-label={t("github.unmapped_assignee_tooltip")} />
            </Tooltip>
          )}
        </span>
      ))}
    </div>
  );
}

function PullRequestCard({ pullRequest }: { pullRequest: TGithubPullRequestLink }) {
  const { t } = useTranslation();
  const stateConfig = PR_STATE_CONFIG[pullRequest.state];
  const StateIcon = stateConfig.icon;

  return (
    <a
      href={pullRequest.url}
      target="_blank"
      rel="noopener noreferrer"
      title={pullRequest.title}
      className="group flex items-center justify-between gap-3 rounded-md border border-subtle px-2.5 py-2 hover:bg-layer-1"
    >
      <div className="flex min-w-0 items-center gap-2.5">
        <Avatar src={pullRequest.author_avatar_url} name={pullRequest.author_login} size="sm" />
        <div className="flex min-w-0 flex-col">
          <span className="truncate text-body-sm-medium text-primary">{pullRequest.title}</span>
          <span className="truncate text-body-xs-regular text-tertiary">
            {pullRequest.repository_full_name}#{pullRequest.pr_number} &middot; {pullRequest.author_login}
          </span>
        </div>
      </div>
      <div className="flex flex-shrink-0 items-center gap-2">
        <span
          className={cn("flex items-center gap-1 rounded-sm px-2 py-0.5 text-11 font-medium", stateConfig.className)}
        >
          <StateIcon className="size-3" />
          {t(`github.state.${pullRequest.state}`)}
        </span>
        <ExternalLink className="size-3.5 text-placeholder opacity-0 group-hover:opacity-100" />
      </div>
    </a>
  );
}
