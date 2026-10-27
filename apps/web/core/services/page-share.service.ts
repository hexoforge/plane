/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// types
import { API_BASE_URL } from "@plane/constants";
import type { TPageShare, TPageShareRole } from "@plane/types";
// services
import { APIService } from "@/services/api.service";

export type TPageShareCreateData = {
  user: string;
  role: TPageShareRole;
};

export type TPageShareUpdateData = {
  role: TPageShareRole;
};

export class PageShareService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  private getPageBaseUrl(workspaceSlug: string, pageId: string, projectId?: string) {
    return projectId
      ? `/api/workspaces/${workspaceSlug}/projects/${projectId}/pages/${pageId}`
      : `/api/workspaces/${workspaceSlug}/wiki/pages/${pageId}`;
  }

  // Share detail routes are flat (not nested under the page) on the API side.
  private getShareDetailUrl(workspaceSlug: string, shareId: string, projectId?: string) {
    return projectId
      ? `/api/workspaces/${workspaceSlug}/projects/${projectId}/shares/${shareId}/`
      : `/api/workspaces/${workspaceSlug}/wiki/shares/${shareId}/`;
  }

  async fetchPageOwner(workspaceSlug: string, pageId: string, projectId?: string): Promise<string | undefined> {
    return this.get(`${this.getPageBaseUrl(workspaceSlug, pageId, projectId)}/`)
      .then((response) => response?.data?.owned_by)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async list(workspaceSlug: string, pageId: string, projectId?: string): Promise<TPageShare[]> {
    return this.get(`${this.getPageBaseUrl(workspaceSlug, pageId, projectId)}/shares/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async create(
    workspaceSlug: string,
    pageId: string,
    data: TPageShareCreateData,
    projectId?: string
  ): Promise<TPageShare> {
    return this.post(`${this.getPageBaseUrl(workspaceSlug, pageId, projectId)}/shares/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async update(
    workspaceSlug: string,
    _pageId: string,
    shareId: string,
    data: TPageShareUpdateData,
    projectId?: string
  ): Promise<TPageShare> {
    return this.patch(this.getShareDetailUrl(workspaceSlug, shareId, projectId), data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async remove(workspaceSlug: string, _pageId: string, shareId: string, projectId?: string): Promise<void> {
    return this.delete(this.getShareDetailUrl(workspaceSlug, shareId, projectId))
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }
}

const pageShareService = new PageShareService();

export default pageShareService;
