/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { Controller, useForm } from "react-hook-form";
import useSWR, { mutate } from "swr";
// plane imports
import { GITHUB_APP_PROJECT_STATE_MAPPING } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import type { TGithubStateMapping } from "@plane/types";
import { ToggleSwitch } from "@plane/ui";
// components
import { StateDropdown } from "@/components/dropdowns/state/dropdown";
// services
import { GithubAppIntegrationService } from "@/services/github-integration.service";

const githubAppIntegrationService = new GithubAppIntegrationService();

const defaultStateMapping: TGithubStateMapping = {
  pr_opened_state: null,
  pr_merged_state: null,
  issue_closed_state: null,
  issue_reopened_state: null,
  auto_create_issues: true,
  sync_comments: true,
};

type Props = {
  workspaceSlug: string;
  projectId: string;
  disabled: boolean;
};

export function GithubProjectStateMappingForm(props: Props) {
  const { workspaceSlug, projectId, disabled } = props;
  // translation
  const { t } = useTranslation();
  // form
  const {
    control,
    handleSubmit,
    reset,
    formState: { isSubmitting, isDirty },
  } = useForm<TGithubStateMapping>({ defaultValues: defaultStateMapping });
  // fetch
  const stateMappingKey = GITHUB_APP_PROJECT_STATE_MAPPING(workspaceSlug, projectId);
  const { isLoading } = useSWR(
    stateMappingKey,
    () => githubAppIntegrationService.getProjectStateMapping(workspaceSlug, projectId),
    { onSuccess: (data) => reset(data) }
  );

  const handleSave = async (formData: TGithubStateMapping) => {
    try {
      const updated = await githubAppIntegrationService.updateProjectStateMapping(workspaceSlug, projectId, formData);
      await mutate(stateMappingKey, updated, false);
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: t("project_settings.github.state_mapping.toasts.saved.title"),
        message: t("project_settings.github.state_mapping.toasts.saved.message"),
      });
    } catch {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("project_settings.github.state_mapping.toasts.not_saved.title"),
        message: t("project_settings.github.state_mapping.toasts.not_saved.message"),
      });
    }
  };

  if (isLoading) {
    return (
      <output className="flex flex-col gap-2" aria-label="Loading state mapping">
        <div className="h-9 w-full animate-pulse rounded-lg bg-layer-1" />
        <div className="h-9 w-full animate-pulse rounded-lg bg-layer-1" />
      </output>
    );
  }

  type TStateMappingKey = "pr_opened_state" | "pr_merged_state" | "issue_closed_state" | "issue_reopened_state";
  const stateFields: { key: TStateMappingKey; label: string }[] = [
    { key: "pr_opened_state", label: t("project_settings.github.state_mapping.pr_opened_state") },
    { key: "pr_merged_state", label: t("project_settings.github.state_mapping.pr_merged_state") },
    { key: "issue_closed_state", label: t("project_settings.github.state_mapping.issue_closed_state") },
    { key: "issue_reopened_state", label: t("project_settings.github.state_mapping.issue_reopened_state") },
  ];

  return (
    <form className="flex flex-col gap-4" onSubmit={handleSubmit(handleSave)}>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {stateFields.map((field) => (
          <div key={field.key} className="flex flex-col gap-1.5">
            <span className="text-body-xs-medium text-secondary">{field.label}</span>
            <Controller
              control={control}
              name={field.key}
              render={({ field: { value, onChange } }) => (
                <StateDropdown
                  projectId={projectId}
                  value={value}
                  onChange={onChange}
                  disabled={disabled}
                  buttonVariant="border-with-text"
                  className="w-full"
                  buttonContainerClassName="w-full"
                />
              )}
            />
          </div>
        ))}
      </div>

      <div className="flex items-center justify-between gap-4 border-t border-subtle pt-4">
        <div className="flex flex-col">
          <span className="text-body-sm-medium text-primary">
            {t("project_settings.github.state_mapping.auto_create_issues")}
          </span>
          <span className="text-body-xs-regular text-tertiary">
            {t("project_settings.github.state_mapping.auto_create_issues_description")}
          </span>
        </div>
        <Controller
          control={control}
          name="auto_create_issues"
          render={({ field: { value, onChange } }) => (
            <ToggleSwitch
              value={value}
              onChange={onChange}
              disabled={disabled}
              label={t("project_settings.github.state_mapping.auto_create_issues")}
            />
          )}
        />
      </div>

      <div className="flex items-center justify-between gap-4 border-t border-subtle pt-4">
        <div className="flex flex-col">
          <span className="text-body-sm-medium text-primary">
            {t("project_settings.github.state_mapping.sync_comments")}
          </span>
          <span className="text-body-xs-regular text-tertiary">
            {t("project_settings.github.state_mapping.sync_comments_description")}
          </span>
        </div>
        <Controller
          control={control}
          name="sync_comments"
          render={({ field: { value, onChange } }) => (
            <ToggleSwitch
              value={value}
              onChange={onChange}
              disabled={disabled}
              label={t("project_settings.github.state_mapping.sync_comments")}
            />
          )}
        />
      </div>

      {!disabled && (
        <div>
          <Button type="submit" variant="primary" disabled={!isDirty} loading={isSubmitting}>
            {t("project_settings.github.state_mapping.save")}
          </Button>
        </div>
      )}
    </form>
  );
}
