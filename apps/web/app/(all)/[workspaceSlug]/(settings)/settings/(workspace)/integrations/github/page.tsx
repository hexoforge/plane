/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect, useRef, useState } from "react";
import { observer } from "mobx-react";
import useSWR, { mutate } from "swr";
// plane imports
import { EUserPermissions, EUserPermissionsLevel, GITHUB_APP_WORKSPACE_INTEGRATION } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { EmptyStateCompact } from "@plane/propel/empty-state";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { useRouter, usePathname, useSearchParams } from "next/navigation";
// components
import { NotAuthorizedView } from "@/components/auth-screens/not-authorized-view";
import { PageHead } from "@/components/core/page-title";
import { GithubWorkspaceConnectionCard } from "@/components/github/workspace-connection-card";
import { SettingsContentWrapper } from "@/components/settings/content-wrapper";
import { SettingsHeading } from "@/components/settings/heading";
// hooks
import { useWorkspace } from "@/hooks/store/use-workspace";
import { useUserPermissions } from "@/hooks/store/user";
// services
import { GithubAppIntegrationService } from "@/services/github-integration.service";
// local imports
import type { Route } from "./+types/page";
import { GithubWorkspaceSettingsHeader } from "./header";

const githubAppIntegrationService = new GithubAppIntegrationService();

function GithubIntegrationSettingsPage({ params }: Route.ComponentProps) {
  const { workspaceSlug } = params;
  // states
  const hasHandledInstallationReturn = useRef(false);
  const [isConnecting, setIsConnecting] = useState(false);
  // router
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  // store hooks
  const { workspaceUserInfo, allowPermissions } = useUserPermissions();
  const { currentWorkspace } = useWorkspace();
  // translation
  const { t } = useTranslation();
  // derived values
  const isWorkspaceAdmin = allowPermissions([EUserPermissions.ADMIN], EUserPermissionsLevel.WORKSPACE);
  const pageTitle = currentWorkspace?.name
    ? `${currentWorkspace.name} - ${t("workspace_settings.settings.github_integration.title")}`
    : undefined;

  const swrKey = isWorkspaceAdmin ? GITHUB_APP_WORKSPACE_INTEGRATION(workspaceSlug) : null;
  const { data: integration, isLoading } = useSWR(swrKey, () =>
    githubAppIntegrationService.getWorkspaceIntegration(workspaceSlug)
  );

  useEffect(() => {
    const installationId = searchParams.get("installation_id");
    if (!installationId || hasHandledInstallationReturn.current || !isWorkspaceAdmin) return;
    hasHandledInstallationReturn.current = true;

    (async () => {
      setIsConnecting(true);
      try {
        await githubAppIntegrationService.connectInstallation(workspaceSlug, Number(installationId));
        await mutate(GITHUB_APP_WORKSPACE_INTEGRATION(workspaceSlug));
        setToast({
          type: TOAST_TYPE.SUCCESS,
          title: t("workspace_settings.settings.github_integration.toasts.connected.title"),
          message: t("workspace_settings.settings.github_integration.toasts.connected.message"),
        });
      } catch {
        setToast({
          type: TOAST_TYPE.ERROR,
          title: t("workspace_settings.settings.github_integration.toasts.not_connected.title"),
          message: t("workspace_settings.settings.github_integration.toasts.not_connected.message"),
        });
      } finally {
        setIsConnecting(false);
        router.replace(pathname);
      }
    })();
  }, [searchParams, workspaceSlug, isWorkspaceAdmin, pathname, router, t]);

  if (workspaceUserInfo && !isWorkspaceAdmin) {
    return <NotAuthorizedView section="settings" className="h-auto" />;
  }

  return (
    <SettingsContentWrapper header={<GithubWorkspaceSettingsHeader />} hugging>
      <PageHead title={pageTitle} />
      <div className="flex w-full flex-col gap-y-6">
        <SettingsHeading
          title={t("workspace_settings.settings.github_integration.heading")}
          description={t("workspace_settings.settings.github_integration.description")}
        />
        {isLoading || isConnecting ? (
          <output className="flex flex-col gap-3" aria-label="Loading GitHub integration status">
            <div className="h-16 w-full animate-pulse rounded-lg bg-layer-1" />
          </output>
        ) : !integration?.configured ? (
          <EmptyStateCompact
            assetKey="settings"
            align="start"
            title={t("workspace_settings.settings.github_integration.not_configured.title")}
            description={t("workspace_settings.settings.github_integration.not_configured.description")}
          />
        ) : integration.installation ? (
          <GithubWorkspaceConnectionCard
            workspaceSlug={workspaceSlug}
            installation={integration.installation}
            onDisconnected={() => mutate(GITHUB_APP_WORKSPACE_INTEGRATION(workspaceSlug))}
          />
        ) : (
          <EmptyStateCompact
            assetKey="settings"
            align="start"
            title={t("workspace_settings.settings.github_integration.heading")}
            description={t("workspace_settings.settings.github_integration.description")}
            actions={
              integration.install_url
                ? [
                    {
                      label: t("workspace_settings.settings.github_integration.install"),
                      variant: "primary",
                      onClick: () => {
                        window.location.href = integration.install_url as string;
                      },
                    },
                  ]
                : undefined
            }
          />
        )}
      </div>
    </SettingsContentWrapper>
  );
}

export default observer(GithubIntegrationSettingsPage);
