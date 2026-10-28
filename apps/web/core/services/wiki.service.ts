/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// types
import { API_BASE_URL } from "@plane/constants";
import type {
  TDocumentPayload,
  TPage,
  TPageComment,
  TPageCollection,
  TPageShare,
  TPageVersion,
  TWikiTree,
} from "@plane/types";
// services
import { APIService } from "@/services/api.service";

export type TWikiPageListParams = {
  collection?: string;
  parent?: string;
  search?: string;
  archived?: boolean;
};

export class WikiService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  // collections
  async fetchCollections(workspaceSlug: string): Promise<TPageCollection[]> {
    return this.get(`/api/workspaces/${workspaceSlug}/wiki/collections/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async createCollection(workspaceSlug: string, data: Partial<TPageCollection>): Promise<TPageCollection> {
    return this.post(`/api/workspaces/${workspaceSlug}/wiki/collections/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async updateCollection(
    workspaceSlug: string,
    collectionId: string,
    data: Partial<TPageCollection>
  ): Promise<TPageCollection> {
    return this.patch(`/api/workspaces/${workspaceSlug}/wiki/collections/${collectionId}/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async deleteCollection(workspaceSlug: string, collectionId: string): Promise<void> {
    return this.delete(`/api/workspaces/${workspaceSlug}/wiki/collections/${collectionId}/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  // tree
  async fetchTree(workspaceSlug: string): Promise<TWikiTree> {
    return this.get(`/api/workspaces/${workspaceSlug}/wiki/tree/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  // pages
  async fetchAll(workspaceSlug: string, params?: TWikiPageListParams): Promise<TPage[]> {
    return this.get(`/api/workspaces/${workspaceSlug}/wiki/pages/`, { params })
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async fetchById(workspaceSlug: string, pageId: string): Promise<TPage> {
    return this.get(`/api/workspaces/${workspaceSlug}/wiki/pages/${pageId}/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async create(workspaceSlug: string, data: Partial<TPage>): Promise<TPage> {
    return this.post(`/api/workspaces/${workspaceSlug}/wiki/pages/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async update(workspaceSlug: string, pageId: string, data: Partial<TPage>): Promise<TPage> {
    return this.patch(`/api/workspaces/${workspaceSlug}/wiki/pages/${pageId}/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async remove(workspaceSlug: string, pageId: string): Promise<void> {
    return this.delete(`/api/workspaces/${workspaceSlug}/wiki/pages/${pageId}/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async archive(workspaceSlug: string, pageId: string): Promise<{ archived_at: string }> {
    return this.post(`/api/workspaces/${workspaceSlug}/wiki/pages/${pageId}/archive/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async restore(workspaceSlug: string, pageId: string): Promise<void> {
    return this.delete(`/api/workspaces/${workspaceSlug}/wiki/pages/${pageId}/archive/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async fetchDescriptionBinary(workspaceSlug: string, pageId: string): Promise<any> {
    return this.get(`/api/workspaces/${workspaceSlug}/wiki/pages/${pageId}/description/`, {
      headers: {
        "Content-Type": "application/octet-stream",
      },
      responseType: "arraybuffer",
    })
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async updateDescription(workspaceSlug: string, pageId: string, data: TDocumentPayload): Promise<any> {
    return this.patch(`/api/workspaces/${workspaceSlug}/wiki/pages/${pageId}/description/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error;
      });
  }

  // versions
  async fetchAllVersions(workspaceSlug: string, pageId: string): Promise<TPageVersion[]> {
    return this.get(`/api/workspaces/${workspaceSlug}/wiki/pages/${pageId}/versions/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async fetchVersionById(workspaceSlug: string, pageId: string, versionId: string): Promise<TPageVersion> {
    return this.get(`/api/workspaces/${workspaceSlug}/wiki/pages/${pageId}/versions/${versionId}/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async restoreVersion(workspaceSlug: string, pageId: string, versionId: string): Promise<void> {
    return this.post(`/api/workspaces/${workspaceSlug}/wiki/pages/${pageId}/versions/${versionId}/restore/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  // shares
  async fetchShares(workspaceSlug: string, pageId: string): Promise<TPageShare[]> {
    return this.get(`/api/workspaces/${workspaceSlug}/wiki/pages/${pageId}/shares/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async createShare(workspaceSlug: string, pageId: string, data: Partial<TPageShare>): Promise<TPageShare> {
    return this.post(`/api/workspaces/${workspaceSlug}/wiki/pages/${pageId}/shares/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async updateShare(workspaceSlug: string, shareId: string, data: Partial<TPageShare>): Promise<TPageShare> {
    return this.patch(`/api/workspaces/${workspaceSlug}/wiki/shares/${shareId}/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async deleteShare(workspaceSlug: string, shareId: string): Promise<void> {
    return this.delete(`/api/workspaces/${workspaceSlug}/wiki/shares/${shareId}/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  // comments
  async fetchComments(workspaceSlug: string, pageId: string): Promise<TPageComment[]> {
    return this.get(`/api/workspaces/${workspaceSlug}/wiki/pages/${pageId}/comments/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async createComment(workspaceSlug: string, pageId: string, data: Partial<TPageComment>): Promise<TPageComment> {
    return this.post(`/api/workspaces/${workspaceSlug}/wiki/pages/${pageId}/comments/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async updateComment(workspaceSlug: string, commentId: string, data: Partial<TPageComment>): Promise<TPageComment> {
    return this.patch(`/api/workspaces/${workspaceSlug}/wiki/comments/${commentId}/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async deleteComment(workspaceSlug: string, commentId: string): Promise<void> {
    return this.delete(`/api/workspaces/${workspaceSlug}/wiki/comments/${commentId}/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }
}
