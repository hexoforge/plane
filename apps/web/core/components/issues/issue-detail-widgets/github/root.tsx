/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import useSWR from "swr";
// plane imports
import { GITHUB_APP_WORK_ITEM_LINKS } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { Collapsible, CollapsibleButton } from "@plane/ui";
// services
import { GithubAppIntegrationService } from "@/services/github-integration.service";
// local imports
import { GithubCollapsibleContent } from "./content";

const githubAppIntegrationService = new GithubAppIntegrationService();

type Props = {
  workspaceSlug: string;
  projectId: string;
  issueId: string;
};

export function GithubCollapsible(props: Props) {
  const { workspaceSlug, projectId, issueId } = props;
  // states
  const [isOpen, setIsOpen] = useState(true);
  // translation
  const { t } = useTranslation();
  // fetch
  const {
    data: links,
    error,
    isLoading,
  } = useSWR(GITHUB_APP_WORK_ITEM_LINKS(workspaceSlug, projectId, issueId), () =>
    githubAppIntegrationService.getWorkItemGithubLinks(workspaceSlug, projectId, issueId)
  );

  if (isLoading) {
    return <div className="h-11 w-full animate-pulse rounded-md bg-layer-1" />;
  }

  if (error || !links) return null;

  const itemCount = links.pull_requests.length + (links.issue_link ? 1 : 0);
  if (itemCount === 0) return null;

  return (
    <Collapsible
      isOpen={isOpen}
      onToggle={() => setIsOpen((prev) => !prev)}
      title={
        <CollapsibleButton
          isOpen={isOpen}
          title={t("github.title")}
          indicatorElement={
            <span className="flex items-center justify-center">
              <p className="text-14 !leading-3 text-tertiary">{itemCount}</p>
            </span>
          }
        />
      }
      buttonClassName="w-full"
    >
      <GithubCollapsibleContent links={links} />
    </Collapsible>
  );
}
