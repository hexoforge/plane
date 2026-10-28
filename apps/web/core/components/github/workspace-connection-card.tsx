/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { Github } from "lucide-react";
// plane imports
import { useTranslation } from "@plane/i18n";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import type { TGithubInstallation } from "@plane/types";
import { AlertModalCore, CustomMenu } from "@plane/ui";
import { renderFormattedDate } from "@plane/utils";
// services
import { GithubAppIntegrationService } from "@/services/github-integration.service";

const githubAppIntegrationService = new GithubAppIntegrationService();

type Props = {
  workspaceSlug: string;
  installation: TGithubInstallation;
  onDisconnected: () => void;
};

export function GithubWorkspaceConnectionCard(props: Props) {
  const { workspaceSlug, installation, onDisconnected } = props;
  // states
  const [isDisconnectModalOpen, setIsDisconnectModalOpen] = useState(false);
  const [isDisconnecting, setIsDisconnecting] = useState(false);
  // translation
  const { t } = useTranslation();

  const handleDisconnect = async () => {
    setIsDisconnecting(true);
    try {
      await githubAppIntegrationService.disconnectInstallation(workspaceSlug);
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: t("workspace_settings.settings.github_integration.toasts.disconnected.title"),
        message: t("workspace_settings.settings.github_integration.toasts.disconnected.message"),
      });
      setIsDisconnectModalOpen(false);
      onDisconnected();
    } catch {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("workspace_settings.settings.github_integration.toasts.not_disconnected.title"),
        message: t("workspace_settings.settings.github_integration.toasts.not_disconnected.message"),
      });
    } finally {
      setIsDisconnecting(false);
    }
  };

  return (
    <div className="flex items-center justify-between gap-4 rounded-lg border border-subtle bg-layer-2 px-4 py-3">
      <div className="flex min-w-0 items-center gap-3">
        <div className="flex size-9 flex-shrink-0 items-center justify-center rounded-full bg-layer-1">
          <Github className="size-4.5 text-secondary" />
        </div>
        <div className="flex min-w-0 flex-col">
          <span className="truncate text-body-sm-medium text-primary">
            {t("workspace_settings.settings.github_integration.connected_as")} {installation.account_login}
          </span>
          <span className="truncate text-body-xs-regular text-tertiary">
            {t("workspace_settings.settings.github_integration.connected_on", {
              date: renderFormattedDate(installation.created_at),
            })}
          </span>
        </div>
        {installation.suspended_at && (
          <span className="bg-amber-50 text-amber-500 flex-shrink-0 rounded-sm px-2 py-1 text-11 font-medium">
            {t("workspace_settings.settings.github_integration.suspended")}
          </span>
        )}
      </div>
      <CustomMenu ellipsis placement="bottom-end" closeOnSelect>
        <CustomMenu.MenuItem
          className="flex items-center gap-2 text-danger-primary"
          onClick={() => setIsDisconnectModalOpen(true)}
        >
          {t("workspace_settings.settings.github_integration.disconnect")}
        </CustomMenu.MenuItem>
      </CustomMenu>
      <AlertModalCore
        isOpen={isDisconnectModalOpen}
        handleClose={() => setIsDisconnectModalOpen(false)}
        handleSubmit={handleDisconnect}
        isSubmitting={isDisconnecting}
        title={t("workspace_settings.settings.github_integration.disconnect_modal.title")}
        content={t("workspace_settings.settings.github_integration.disconnect_modal.content")}
      />
    </div>
  );
}
