/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import useSWR from "swr";
// plane imports
import { EUserPermissions, EUserPermissionsLevel, GITHUB_APP_WORKSPACE_INTEGRATION } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { EmptyStateCompact } from "@plane/propel/empty-state";
// components
import { NotAuthorizedView } from "@/components/auth-screens/not-authorized-view";
import { PageHead } from "@/components/core/page-title";
import { GithubProjectRepositoriesSection } from "@/components/github/project-repositories-section";
import { GithubProjectStateMappingForm } from "@/components/github/project-state-mapping-form";
import { SettingsContentWrapper } from "@/components/settings/content-wrapper";
import { SettingsHeading } from "@/components/settings/heading";
// hooks
import { useProject } from "@/hooks/store/use-project";
import { useUserPermissions } from "@/hooks/store/user";
// services
import { GithubAppIntegrationService } from "@/services/github-integration.service";
// local imports
import type { Route } from "./+types/page";
import { GithubProjectSettingsHeader } from "./header";

const githubAppIntegrationService = new GithubAppIntegrationService();

function ProjectGithubSettingsPage({ params }: Route.ComponentProps) {
  const { workspaceSlug, projectId } = params;
  // store hooks
  const { workspaceUserInfo, allowPermissions } = useUserPermissions();
  const { currentProjectDetails } = useProject();
  // translation
  const { t } = useTranslation();
  // derived values
  const canPerformProjectAdminActions = allowPermissions([EUserPermissions.ADMIN], EUserPermissionsLevel.PROJECT);
  const pageTitle = currentProjectDetails?.name
    ? `${currentProjectDetails.name} - ${t("project_settings.github.label")}`
    : undefined;

  const { data: workspaceIntegration, isLoading } = useSWR(
    canPerformProjectAdminActions ? GITHUB_APP_WORKSPACE_INTEGRATION(workspaceSlug) : null,
    () => githubAppIntegrationService.getWorkspaceIntegration(workspaceSlug)
  );

  if (workspaceUserInfo && !canPerformProjectAdminActions) {
    return <NotAuthorizedView section="settings" isProjectView className="h-auto" />;
  }

  const isGithubConnected = !!workspaceIntegration?.configured && !!workspaceIntegration?.installation;

  return (
    <SettingsContentWrapper header={<GithubProjectSettingsHeader />} hugging>
      <PageHead title={pageTitle} />
      <div className="flex w-full flex-col gap-y-6">
        <SettingsHeading
          title={t("project_settings.github.heading")}
          description={t("project_settings.github.description")}
        />
        {isLoading ? (
          <output className="flex flex-col gap-3" aria-label="Loading GitHub settings">
            <div className="h-16 w-full animate-pulse rounded-lg bg-layer-1" />
          </output>
        ) : !isGithubConnected ? (
          <EmptyStateCompact
            assetKey="settings"
            align="start"
            title={t("project_settings.github.not_configured.title")}
            description={t("project_settings.github.not_configured.description")}
          />
        ) : (
          <div className="flex flex-col gap-8">
            <GithubProjectRepositoriesSection
              workspaceSlug={workspaceSlug}
              projectId={projectId}
              disabled={!canPerformProjectAdminActions}
            />
            <div className="flex flex-col gap-3 border-t border-subtle pt-6">
              <div className="flex flex-col gap-1">
                <h4 className="text-body-sm-medium text-primary">{t("project_settings.github.state_mapping.title")}</h4>
                <p className="text-body-xs-regular text-tertiary">
                  {t("project_settings.github.state_mapping.description")}
                </p>
              </div>
              <GithubProjectStateMappingForm
                workspaceSlug={workspaceSlug}
                projectId={projectId}
                disabled={!canPerformProjectAdminActions}
              />
            </div>
          </div>
        )}
      </div>
    </SettingsContentWrapper>
  );
}

export default observer(ProjectGithubSettingsPage);
