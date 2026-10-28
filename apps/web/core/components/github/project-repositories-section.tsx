/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { ExternalLink, Lock, Plus } from "lucide-react";
import useSWR, { mutate } from "swr";
// plane imports
import { GITHUB_APP_AVAILABLE_REPOSITORIES, GITHUB_APP_PROJECT_REPOSITORIES } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import { EmptyStateCompact } from "@plane/propel/empty-state";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import type { TGithubAvailableRepository, TGithubLinkedRepository } from "@plane/types";
import { AlertModalCore, CustomMenu } from "@plane/ui";
// services
import { GithubAppIntegrationService } from "@/services/github-integration.service";

const githubAppIntegrationService = new GithubAppIntegrationService();

type Props = {
  workspaceSlug: string;
  projectId: string;
  disabled: boolean;
};

export function GithubProjectRepositoriesSection(props: Props) {
  const { workspaceSlug, projectId, disabled } = props;
  // states
  const [isAdding, setIsAdding] = useState(false);
  const [repositoryPendingRemoval, setRepositoryPendingRemoval] = useState<TGithubLinkedRepository | null>(null);
  const [isRemoving, setIsRemoving] = useState(false);
  // translation
  const { t } = useTranslation();
  // fetch
  const linkedRepositoriesKey = GITHUB_APP_PROJECT_REPOSITORIES(workspaceSlug, projectId);
  const { data: linkedRepositories, isLoading: isLoadingLinked } = useSWR(linkedRepositoriesKey, () =>
    githubAppIntegrationService.getProjectLinkedRepositories(workspaceSlug, projectId)
  );
  const { data: availableRepositories } = useSWR(GITHUB_APP_AVAILABLE_REPOSITORIES(workspaceSlug), () =>
    githubAppIntegrationService.getAvailableRepositories(workspaceSlug)
  );

  const linkedRepoIds = new Set((linkedRepositories ?? []).map((repo) => repo.repo_id));
  const addableRepositories = (availableRepositories ?? []).filter((repo) => !linkedRepoIds.has(repo.id));

  const handleAdd = async (repository: TGithubAvailableRepository) => {
    setIsAdding(true);
    try {
      await githubAppIntegrationService.addProjectRepository(workspaceSlug, projectId, repository);
      await mutate(linkedRepositoriesKey);
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: t("project_settings.github.repositories.toasts.added.title"),
        message: t("project_settings.github.repositories.toasts.added.message"),
      });
    } catch {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("project_settings.github.repositories.toasts.not_added.title"),
        message: t("project_settings.github.repositories.toasts.not_added.message"),
      });
    } finally {
      setIsAdding(false);
    }
  };

  const handleRemove = async () => {
    if (!repositoryPendingRemoval) return;
    setIsRemoving(true);
    try {
      await githubAppIntegrationService.removeProjectRepository(workspaceSlug, projectId, repositoryPendingRemoval.id);
      await mutate(linkedRepositoriesKey);
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: t("project_settings.github.repositories.toasts.removed.title"),
        message: t("project_settings.github.repositories.toasts.removed.message"),
      });
      setRepositoryPendingRemoval(null);
    } catch {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("project_settings.github.repositories.toasts.not_removed.title"),
        message: t("project_settings.github.repositories.toasts.not_removed.message"),
      });
    } finally {
      setIsRemoving(false);
    }
  };

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between gap-4">
        <h4 className="text-body-sm-medium text-primary">{t("project_settings.github.repositories.title")}</h4>
        {!disabled && (
          <CustomMenu
            placement="bottom-end"
            closeOnSelect
            disabled={isAdding || addableRepositories.length === 0}
            customButton={
              <Button variant="primary" size="sm" disabled={isAdding || addableRepositories.length === 0}>
                <Plus className="size-3.5" />
                {t("project_settings.github.repositories.add")}
              </Button>
            }
          >
            {addableRepositories.map((repo) => (
              <CustomMenu.MenuItem
                key={repo.id}
                disabled={!!repo.linked_project_id}
                className="flex items-center justify-between gap-2"
                onClick={() => handleAdd(repo)}
              >
                <span className="truncate">{repo.full_name}</span>
                {repo.linked_project_id && (
                  <span className="flex-shrink-0 text-11 text-placeholder">
                    {t("project_settings.github.repositories.already_linked")}
                  </span>
                )}
              </CustomMenu.MenuItem>
            ))}
          </CustomMenu>
        )}
      </div>

      {isLoadingLinked ? (
        <output className="flex flex-col gap-2" aria-label="Loading linked repositories">
          <div className="h-11 w-full animate-pulse rounded-lg bg-layer-1" />
          <div className="h-11 w-full animate-pulse rounded-lg bg-layer-1" />
        </output>
      ) : linkedRepositories && linkedRepositories.length > 0 ? (
        <div className="flex flex-col gap-2">
          {linkedRepositories.map((repo) => (
            <div
              key={repo.id}
              className="flex items-center justify-between gap-4 rounded-lg border border-subtle bg-layer-2 px-3.5 py-2.5"
            >
              <div className="flex min-w-0 items-center gap-2">
                <span className="truncate text-body-sm-medium text-primary">{repo.full_name}</span>
                {repo.private && (
                  <span className="flex flex-shrink-0 items-center gap-1 rounded-sm bg-layer-1 px-2 py-0.5 text-11 font-medium text-secondary">
                    <Lock className="size-3" />
                    {t("project_settings.github.repositories.private")}
                  </span>
                )}
              </div>
              <div className="flex flex-shrink-0 items-center gap-1">
                <a
                  href={repo.html_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label={`Open ${repo.full_name} on GitHub`}
                  className="flex size-7 items-center justify-center rounded-sm text-tertiary hover:bg-layer-1 hover:text-secondary"
                >
                  <ExternalLink className="size-4" />
                </a>
                {!disabled && (
                  <CustomMenu ellipsis placement="bottom-end" closeOnSelect>
                    <CustomMenu.MenuItem
                      className="text-danger-primary"
                      onClick={() => setRepositoryPendingRemoval(repo)}
                    >
                      {t("common.remove")}
                    </CustomMenu.MenuItem>
                  </CustomMenu>
                )}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <EmptyStateCompact
          assetKey="link"
          align="start"
          title={t("project_settings.github.repositories.empty.title")}
          description={t("project_settings.github.repositories.empty.description")}
        />
      )}

      <AlertModalCore
        isOpen={!!repositoryPendingRemoval}
        handleClose={() => setRepositoryPendingRemoval(null)}
        handleSubmit={handleRemove}
        isSubmitting={isRemoving}
        title={t("project_settings.github.repositories.remove_modal.title")}
        content={t("project_settings.github.repositories.remove_modal.content")}
      />
    </div>
  );
}
