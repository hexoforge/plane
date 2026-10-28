/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { API_BASE_URL } from "@plane/constants";
import type {
  TGithubAvailableRepository,
  TGithubIntegrationStatus,
  TGithubLinkedRepository,
  TGithubStateMapping,
  TWorkItemGithubLinks,
} from "@plane/types";
import { APIService } from "@/services/api.service";

export class GithubAppIntegrationService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  async getWorkspaceIntegration(workspaceSlug: string): Promise<TGithubIntegrationStatus> {
    return this.get(`/api/workspaces/${workspaceSlug}/integrations/github/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async connectInstallation(workspaceSlug: string, installationId: number): Promise<TGithubIntegrationStatus> {
    return this.post(`/api/workspaces/${workspaceSlug}/integrations/github/installation/`, {
      installation_id: installationId,
    })
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async disconnectInstallation(workspaceSlug: string): Promise<void> {
    return this.delete(`/api/workspaces/${workspaceSlug}/integrations/github/installation/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async getAvailableRepositories(workspaceSlug: string): Promise<TGithubAvailableRepository[]> {
    return this.get(`/api/workspaces/${workspaceSlug}/integrations/github/repositories/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async getProjectLinkedRepositories(workspaceSlug: string, projectId: string): Promise<TGithubLinkedRepository[]> {
    return this.get(`/api/workspaces/${workspaceSlug}/projects/${projectId}/github/repositories/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async addProjectRepository(
    workspaceSlug: string,
    projectId: string,
    repoId: number
  ): Promise<TGithubLinkedRepository> {
    return this.post(`/api/workspaces/${workspaceSlug}/projects/${projectId}/github/repositories/`, {
      repo_id: repoId,
    })
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async removeProjectRepository(workspaceSlug: string, projectId: string, linkedRepositoryId: string): Promise<void> {
    return this.delete(
      `/api/workspaces/${workspaceSlug}/projects/${projectId}/github/repositories/${linkedRepositoryId}/`
    )
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async getProjectStateMapping(workspaceSlug: string, projectId: string): Promise<TGithubStateMapping> {
    return this.get(`/api/workspaces/${workspaceSlug}/projects/${projectId}/github/state-mapping/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async updateProjectStateMapping(
    workspaceSlug: string,
    projectId: string,
    data: Partial<TGithubStateMapping>
  ): Promise<TGithubStateMapping> {
    return this.put(`/api/workspaces/${workspaceSlug}/projects/${projectId}/github/state-mapping/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async getWorkItemGithubLinks(
    workspaceSlug: string,
    projectId: string,
    issueId: string
  ): Promise<TWorkItemGithubLinks> {
    return this.get(`/api/workspaces/${workspaceSlug}/projects/${projectId}/issues/${issueId}/github/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }
}
