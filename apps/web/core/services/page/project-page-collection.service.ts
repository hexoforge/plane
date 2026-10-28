/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// types
import { API_BASE_URL } from "@plane/constants";
import type { TPageCollection } from "@plane/types";
// services
import { APIService } from "@/services/api.service";

export class ProjectPageCollectionService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  async fetchAll(workspaceSlug: string, projectId: string): Promise<TPageCollection[]> {
    return this.get(`/api/workspaces/${workspaceSlug}/projects/${projectId}/page-collections/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async create(workspaceSlug: string, projectId: string, data: Partial<TPageCollection>): Promise<TPageCollection> {
    return this.post(`/api/workspaces/${workspaceSlug}/projects/${projectId}/page-collections/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async update(
    workspaceSlug: string,
    projectId: string,
    collectionId: string,
    data: Partial<TPageCollection>
  ): Promise<TPageCollection> {
    return this.patch(`/api/workspaces/${workspaceSlug}/projects/${projectId}/page-collections/${collectionId}/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async remove(workspaceSlug: string, projectId: string, collectionId: string): Promise<void> {
    return this.delete(`/api/workspaces/${workspaceSlug}/projects/${projectId}/page-collections/${collectionId}/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }
}
