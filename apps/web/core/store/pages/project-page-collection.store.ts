/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { unset, set, orderBy } from "lodash-es";
import { makeObservable, observable, runInAction, action, computed } from "mobx";
import { computedFn } from "mobx-utils";
// types
import { EUserPermissions } from "@plane/constants";
import type { TPageCollection } from "@plane/types";
import { EUserProjectRoles } from "@plane/types";
// services
import { ProjectPageCollectionService } from "@/services/page";
// store
import type { CoreRootStore } from "../root.store";

type TLoader = "init-loader" | "mutation-loader" | undefined;

type TError = { title: string; description: string };

const ROLE_PERMISSIONS_TO_MANAGE_COLLECTIONS = new Set([
  EUserPermissions.ADMIN,
  EUserPermissions.MEMBER,
  EUserProjectRoles.ADMIN,
  EUserProjectRoles.MEMBER,
]);

export interface IProjectPageCollectionStore {
  // observables
  loader: TLoader;
  data: Record<string, TPageCollection>; // collectionId => PageCollection
  error: TError | undefined;
  // helper actions
  getCollectionById: (collectionId: string) => TPageCollection | undefined;
  getCollectionIdsByProject: (projectId: string) => string[];
  getDefaultCollectionId: (projectId: string) => string | undefined;
  canCurrentUserManageCollections: boolean;
  // actions
  fetchCollections: (workspaceSlug: string, projectId: string) => Promise<TPageCollection[] | undefined>;
  createCollection: (
    workspaceSlug: string,
    projectId: string,
    data: Partial<TPageCollection>
  ) => Promise<TPageCollection | undefined>;
  updateCollection: (
    workspaceSlug: string,
    projectId: string,
    collectionId: string,
    data: Partial<TPageCollection>
  ) => Promise<TPageCollection | undefined>;
  removeCollection: (workspaceSlug: string, projectId: string, collectionId: string) => Promise<void>;
}

export class ProjectPageCollectionStore implements IProjectPageCollectionStore {
  // observables
  loader: TLoader = undefined;
  data: Record<string, TPageCollection> = {};
  error: TError | undefined = undefined;
  // service
  service: ProjectPageCollectionService;

  constructor(private store: CoreRootStore) {
    makeObservable(this, {
      // observables
      loader: observable.ref,
      data: observable,
      error: observable,
      // computed
      canCurrentUserManageCollections: computed,
      // actions
      fetchCollections: action,
      createCollection: action,
      updateCollection: action,
      removeCollection: action,
    });
    this.service = new ProjectPageCollectionService();
  }

  get canCurrentUserManageCollections() {
    const { workspaceSlug, projectId } = this.store.router;
    const currentUserProjectRole = this.store.user.permission.getProjectRoleByWorkspaceSlugAndProjectId(
      workspaceSlug?.toString() || "",
      projectId?.toString() || ""
    );
    return !!currentUserProjectRole && ROLE_PERMISSIONS_TO_MANAGE_COLLECTIONS.has(currentUserProjectRole);
  }

  getCollectionById = computedFn((collectionId: string) => this.data?.[collectionId] || undefined);

  getCollectionIdsByProject = computedFn((projectId: string) => {
    const collections = Object.values(this.data || {}).filter((collection) => collection.project === projectId);
    return orderBy(collections, ["sort_order"], ["asc"]).map((collection) => collection.id);
  });

  getDefaultCollectionId = computedFn(
    (projectId: string) =>
      Object.values(this.data || {}).find((collection) => collection.project === projectId && collection.is_default)
        ?.id
  );

  /**
   * @description fetch all the collections of a project
   */
  fetchCollections = async (workspaceSlug: string, projectId: string) => {
    try {
      if (!workspaceSlug || !projectId) return undefined;

      runInAction(() => {
        this.loader = this.getCollectionIdsByProject(projectId).length ? "mutation-loader" : "init-loader";
        this.error = undefined;
      });

      const collections = await this.service.fetchAll(workspaceSlug, projectId);
      runInAction(() => {
        collections.forEach((collection) => {
          if (collection.id) set(this.data, [collection.id], collection);
        });
        this.loader = undefined;
      });

      return collections;
    } catch (error) {
      runInAction(() => {
        this.loader = undefined;
        this.error = {
          title: "Failed",
          description: "Failed to fetch the collections, Please try again later.",
        };
      });
      throw error;
    }
  };

  /**
   * @description create a new collection
   */
  createCollection = async (workspaceSlug: string, projectId: string, data: Partial<TPageCollection>) => {
    try {
      const collection = await this.service.create(workspaceSlug, projectId, data);
      runInAction(() => {
        if (collection?.id) set(this.data, [collection.id], collection);
      });
      return collection;
    } catch (error) {
      runInAction(() => {
        this.error = {
          title: "Failed",
          description: "Failed to create the collection, Please try again later.",
        };
      });
      throw error;
    }
  };

  /**
   * @description rename or update an existing collection
   */
  updateCollection = async (
    workspaceSlug: string,
    projectId: string,
    collectionId: string,
    data: Partial<TPageCollection>
  ) => {
    const currentCollection = this.getCollectionById(collectionId);
    try {
      runInAction(() => {
        set(this.data, [collectionId], { ...currentCollection, ...data });
      });
      const collection = await this.service.update(workspaceSlug, projectId, collectionId, data);
      runInAction(() => {
        set(this.data, [collectionId], collection);
      });
      return collection;
    } catch (error) {
      runInAction(() => {
        if (currentCollection) set(this.data, [collectionId], currentCollection);
        this.error = {
          title: "Failed",
          description: "Failed to update the collection, Please try again later.",
        };
      });
      throw error;
    }
  };

  /**
   * @description delete a collection, the default collection of a project cannot be deleted
   */
  removeCollection = async (workspaceSlug: string, projectId: string, collectionId: string) => {
    const collection = this.getCollectionById(collectionId);
    if (collection?.is_default) throw new Error("The General collection cannot be deleted.");

    await this.service.remove(workspaceSlug, projectId, collectionId);
    runInAction(() => {
      unset(this.data, [collectionId]);
    });
  };
}
