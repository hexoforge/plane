/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { AlertCircle, CheckCircle2 } from "lucide-react";
import useSWR, { mutate } from "swr";
// plane imports
import { GITHUB_APP_REPOSITORY_BACKFILL } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import type { TGithubBackfillRun, TGithubLinkedRepository } from "@plane/types";
import { Checkbox, EModalWidth, ModalCore } from "@plane/ui";
// services
import { GithubAppIntegrationService } from "@/services/github-integration.service";

const githubAppIntegrationService = new GithubAppIntegrationService();

const ACTIVE_STATUSES = new Set(["queued", "running"]);

type Props = {
  workspaceSlug: string;
  projectId: string;
  repository: TGithubLinkedRepository;
  isOpen: boolean;
  handleClose: () => void;
};

export function GithubImportExistingModal(props: Props) {
  const { workspaceSlug, projectId, repository, isOpen, handleClose } = props;
  const [includeClosedIssues, setIncludeClosedIssues] = useState(false);
  const [isStarting, setIsStarting] = useState(false);
  const { t } = useTranslation();

  const statusKey = GITHUB_APP_REPOSITORY_BACKFILL(workspaceSlug, projectId, repository.id);
  const { data: run } = useSWR(
    isOpen ? statusKey : null,
    () => githubAppIntegrationService.getRepositoryBackfillStatus(workspaceSlug, projectId, repository.id),
    { refreshInterval: (latest) => (latest && ACTIVE_STATUSES.has(latest.status) ? 2000 : 0) }
  );

  const isActive = !!run && ACTIVE_STATUSES.has(run.status);

  const handleStart = async () => {
    setIsStarting(true);
    try {
      await githubAppIntegrationService.startRepositoryBackfill(
        workspaceSlug,
        projectId,
        repository.id,
        includeClosedIssues
      );
      await mutate(statusKey);
    } catch {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("project_settings.github.repositories.backfill.toasts.not_started.title"),
        message: t("project_settings.github.repositories.backfill.toasts.not_started.message"),
      });
    } finally {
      setIsStarting(false);
    }
  };

  const renderProgress = (currentRun: TGithubBackfillRun) => (
    <div className="flex flex-col gap-3">
      <output className="flex items-center gap-2 text-body-sm-medium text-primary" aria-label="Import in progress">
        <span className="size-3.5 flex-shrink-0 animate-spin rounded-full border-2 border-subtle border-t-accent-strong" />
        {t("project_settings.github.repositories.backfill.in_progress")}
      </output>
      <div className="flex flex-col gap-1 text-body-xs-regular text-tertiary">
        <span>
          {t("project_settings.github.repositories.backfill.issues_count", {
            imported: currentRun.imported_issues,
            total: currentRun.total_issues,
          })}
        </span>
        <span>
          {t("project_settings.github.repositories.backfill.pull_requests_count", {
            linked: currentRun.linked_pull_requests,
            total: currentRun.total_pull_requests,
          })}
        </span>
      </div>
    </div>
  );

  const renderCompleted = (currentRun: TGithubBackfillRun) => (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-2 text-body-sm-medium text-primary">
        <CheckCircle2 className="size-4 flex-shrink-0 text-success-primary" />
        {t("project_settings.github.repositories.backfill.completed")}
      </div>
      <div className="flex flex-col gap-1 text-body-xs-regular text-tertiary">
        <span>
          {t("project_settings.github.repositories.backfill.issues_count", {
            imported: currentRun.imported_issues,
            total: currentRun.total_issues,
          })}
        </span>
        <span>
          {t("project_settings.github.repositories.backfill.pull_requests_count", {
            linked: currentRun.linked_pull_requests,
            total: currentRun.total_pull_requests,
          })}
        </span>
      </div>
    </div>
  );

  const renderFailed = (currentRun: TGithubBackfillRun) => (
    <div className="flex items-start gap-2 rounded-lg bg-layer-1 p-3 text-body-sm-regular text-danger-primary">
      <AlertCircle className="size-4 flex-shrink-0" />
      <span>{currentRun.error || t("project_settings.github.repositories.backfill.failed")}</span>
    </div>
  );

  return (
    <ModalCore isOpen={isOpen} handleClose={handleClose} width={EModalWidth.LG}>
      <div className="flex flex-col gap-4 p-5">
        <div className="flex flex-col gap-1">
          <h3 className="text-body-md-medium text-primary">
            {t("project_settings.github.repositories.backfill.title")}
          </h3>
          <p className="text-body-xs-regular text-tertiary">
            {t("project_settings.github.repositories.backfill.description", { repo: repository.full_name })}
          </p>
        </div>

        {run && run.status === "running" && renderProgress(run)}
        {run && run.status === "queued" && renderProgress(run)}
        {run && run.status === "completed" && renderCompleted(run)}
        {run && run.status === "failed" && renderFailed(run)}

        {!isActive && (
          <div className="flex items-center gap-2">
            <Checkbox
              id="include-closed-issues"
              checked={includeClosedIssues}
              onChange={(e) => setIncludeClosedIssues(e.target.checked)}
              disabled={isStarting}
            />
            <label htmlFor="include-closed-issues" className="text-body-sm-regular text-secondary">
              {t("project_settings.github.repositories.backfill.include_closed_issues")}
            </label>
          </div>
        )}

        <div className="flex items-center justify-end gap-2 border-t border-subtle pt-4">
          <Button variant="secondary" size="sm" onClick={handleClose}>
            {t("common.close")}
          </Button>
          {!isActive && (
            <Button variant="primary" size="sm" loading={isStarting} onClick={handleStart}>
              {run && run.status !== "queued"
                ? t("project_settings.github.repositories.backfill.import_again")
                : t("project_settings.github.repositories.backfill.start")}
            </Button>
          )}
        </div>
      </div>
    </ModalCore>
  );
}
