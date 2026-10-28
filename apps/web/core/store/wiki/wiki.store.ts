/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { set, unset } from "lodash-es";
import { action, computed, makeObservable, observable, runInAction } from "mobx";
import { computedFn } from "mobx-utils";
// constants
import { EUserPermissions } from "@plane/constants";
import type {
  TPage,
  TPageComment,
  TPageCollection,
  TPageShare,
  TPageShareRole,
  TWikiTreeNode,
} from "@plane/types";
// services
import { WikiService } from "@/services/wiki.service";
import type { TWikiPageListParams } from "@/services/wiki.service";
// store
import type { CoreRootStore } from "../root.store";
import type { TWikiPage } from "../pages/wiki-page";
import { WikiPage } from "../pages/wiki-page";

type TLoader = "init-loader" | "mutation-loader" | undefined;

type TError = { title: string; description: string };

export interface IWikiStore {
  // observables
  loader: TLoader;
  data: Record<string, TWikiPage>;
  collections: Record<string, TPageCollection>;
  treeNodes: TWikiTreeNode[];
  shares: Record<string, TPageShare[]>;
  comments: Record<string, TPageComment[]>;
  error: TError | undefined;
  searchQuery: string;
  // computed
  collectionIds: string[];
  canCurrentUserCreatePage: boolean;
  canCurrentUserCreatePrivateCollection: boolean;
  // helpers
  getPageById: (pageId: string) => TWikiPage | undefined;
  getCollectionById: (collectionId: string) => TPageCollection | undefined;
  getChildPageIds: (collectionId: string, parentId: string | null) => string[];
  getArchivedPageNodes: () => TWikiTreeNode[];
  getCurrentUserShareRole: (pageId: string) => TPageShareRole | undefined;
  updateSearchQuery: (query: string) => void;
  // actions
  fetchTree: (workspaceSlug: string) => Promise<void>;
  fetchCollections: (workspaceSlug: string) => Promise<TPageCollection[] | undefined>;
  createCollection: (workspaceSlug: string, data: Partial<TPageCollection>) => Promise<TPageCollection | undefined>;
  updateCollection: (
    workspaceSlug: string,
    collectionId: string,
    data: Partial<TPageCollection>
  ) => Promise<void>;
  deleteCollection: (workspaceSlug: string, collectionId: string) => Promise<void>;
  fetchPagesList: (workspaceSlug: string, params?: TWikiPageListParams) => Promise<TPage[] | undefined>;
  fetchPageDetails: (workspaceSlug: string, pageId: string) => Promise<TPage | undefined>;
  createPage: (pageData: Partial<TPage>) => Promise<TPage | undefined>;
  removePage: (params: { pageId: string }) => Promise<void>;
  restoreArchivedPage: (workspaceSlug: string, pageId: string) => Promise<void>;
  fetchShares: (workspaceSlug: string, pageId: string) => Promise<TPageShare[] | undefined>;
  createShare: (workspaceSlug: string, pageId: string, data: Partial<TPageShare>) => Promise<void>;
  updateShare: (workspaceSlug: string, pageId: string, shareId: string, data: Partial<TPageShare>) => Promise<void>;
  deleteShare: (workspaceSlug: string, pageId: string, shareId: string) => Promise<void>;
  fetchComments: (workspaceSlug: string, pageId: string) => Promise<TPageComment[] | undefined>;
  createComment: (workspaceSlug: string, pageId: string, data: Partial<TPageComment>) => Promise<void>;
  updateComment: (
    workspaceSlug: string,
    pageId: string,
    commentId: string,
    data: Partial<TPageComment>
  ) => Promise<void>;
  deleteComment: (workspaceSlug: string, pageId: string, commentId: string) => Promise<void>;
}

export class WikiStore implements IWikiStore {
  loader: TLoader = "init-loader";
  data: Record<string, TWikiPage> = {};
  collections: Record<string, TPageCollection> = {};
  treeNodes: TWikiTreeNode[] = [];
  shares: Record<string, TPageShare[]> = {};
  comments: Record<string, TPageComment[]> = {};
  error: TError | undefined = undefined;
  searchQuery: string = "";
  // service
  service: WikiService;
  rootStore: CoreRootStore;

  constructor(private store: CoreRootStore) {
    makeObservable(this, {
      loader: observable.ref,
      data: observable,
      collections: observable,
      treeNodes: observable,
      shares: observable,
      comments: observable,
      error: observable,
      searchQuery: observable.ref,
      collectionIds: computed,
      canCurrentUserCreatePage: computed,
      canCurrentUserCreatePrivateCollection: computed,
      updateSearchQuery: action,
      fetchTree: action,
      fetchCollections: action,
      createCollection: action,
      updateCollection: action,
      deleteCollection: action,
      fetchPagesList: action,
      fetchPageDetails: action,
      createPage: action,
      removePage: action,
      restoreArchivedPage: action,
      fetchShares: action,
      createShare: action,
      updateShare: action,
      deleteShare: action,
      fetchComments: action,
      createComment: action,
      updateComment: action,
      deleteComment: action,
    });
    this.rootStore = store;
    this.service = new WikiService();
  }

  private get workspaceRole(): EUserPermissions | undefined {
    const { workspaceSlug } = this.store.router;
    if (!workspaceSlug) return undefined;
    return this.store.user.permission.getWorkspaceRoleByWorkspaceSlug(workspaceSlug.toString()) as
      | EUserPermissions
      | undefined;
  }

  get collectionIds() {
    return Object.keys(this.collections);
  }

  get canCurrentUserCreatePage() {
    return !!this.workspaceRole && this.workspaceRole >= EUserPermissions.MEMBER;
  }

  get canCurrentUserCreatePrivateCollection() {
    return this.workspaceRole === EUserPermissions.ADMIN;
  }

  getPageById = computedFn((pageId: string) => this.data?.[pageId] || undefined);

  getCollectionById = computedFn((collectionId: string) => this.collections?.[collectionId] || undefined);

  getChildPageIds = computedFn((collectionId: string, parentId: string | null) =>
    this.treeNodes
      .filter((node) => node.collection === collectionId && node.parent === parentId && !node.archived_at)
      .toSorted((a, b) => a.sort_order - b.sort_order)
      .map((node) => node.id)
  );

  getArchivedPageNodes = computedFn(() => this.treeNodes.filter((node) => !!node.archived_at));

  getCurrentUserShareRole = computedFn((pageId: string): TPageShareRole | undefined => {
    const currentUserId = this.store.user.data?.id;
    if (!currentUserId) return undefined;
    const pageShares = this.shares[pageId];
    return pageShares?.find((share) => share.user === currentUserId)?.role;
  });

  updateSearchQuery = (query: string) => {
    runInAction(() => {
      this.searchQuery = query;
    });
  };

  fetchTree = async (workspaceSlug: string) => {
    try {
      runInAction(() => {
        this.loader = this.treeNodes.length ? "mutation-loader" : "init-loader";
        this.error = undefined;
      });
      const tree = await this.service.fetchTree(workspaceSlug);
      runInAction(() => {
        tree.collections.forEach((collection) => set(this.collections, [collection.id], collection));
        this.treeNodes = tree.pages;
        this.loader = undefined;
      });
    } catch (error) {
      runInAction(() => {
        this.loader = undefined;
        this.error = { title: "Failed", description: "Failed to load the wiki, please try again later." };
      });
      throw error;
    }
  };

  fetchCollections = async (workspaceSlug: string) => {
    try {
      const collections = await this.service.fetchCollections(workspaceSlug);
      runInAction(() => {
        collections.forEach((collection) => set(this.collections, [collection.id], collection));
      });
      return collections;
    } catch (error) {
      runInAction(() => {
        this.error = { title: "Failed", description: "Failed to load collections, please try again later." };
      });
      throw error;
    }
  };

  createCollection = async (workspaceSlug: string, data: Partial<TPageCollection>) => {
    const collection = await this.service.createCollection(workspaceSlug, data);
    runInAction(() => {
      set(this.collections, [collection.id], collection);
    });
    return collection;
  };

  updateCollection = async (workspaceSlug: string, collectionId: string, data: Partial<TPageCollection>) => {
    const currentCollection = this.collections[collectionId];
    runInAction(() => {
      set(this.collections, [collectionId], { ...currentCollection, ...data });
    });
    try {
      const collection = await this.service.updateCollection(workspaceSlug, collectionId, data);
      runInAction(() => {
        set(this.collections, [collectionId], collection);
      });
    } catch (error) {
      runInAction(() => {
        set(this.collections, [collectionId], currentCollection);
      });
      throw error;
    }
  };

  deleteCollection = async (workspaceSlug: string, collectionId: string) => {
    await this.service.deleteCollection(workspaceSlug, collectionId);
    runInAction(() => {
      unset(this.collections, [collectionId]);
      this.treeNodes = this.treeNodes.filter((node) => node.collection !== collectionId);
    });
  };

  fetchPagesList = async (workspaceSlug: string, params?: TWikiPageListParams) => {
    try {
      runInAction(() => {
        this.loader = "mutation-loader";
        this.error = undefined;
      });
      const pages = await this.service.fetchAll(workspaceSlug, params);
      runInAction(() => {
        pages.forEach((page) => {
          if (!page?.id) return;
          const existingPage = this.getPageById(page.id);
          if (existingPage) existingPage.mutateProperties(page, false);
          else set(this.data, [page.id], new WikiPage(this.store, page));
        });
        this.loader = undefined;
      });
      return pages;
    } catch (error) {
      runInAction(() => {
        this.loader = undefined;
        this.error = { title: "Failed", description: "Failed to fetch pages, please try again later." };
      });
      throw error;
    }
  };

  fetchPageDetails = async (workspaceSlug: string, pageId: string) => {
    try {
      if (!workspaceSlug || !pageId) return undefined;
      const existingPage = this.getPageById(pageId);
      runInAction(() => {
        this.loader = existingPage ? "mutation-loader" : "init-loader";
        this.error = undefined;
      });
      const page = await this.service.fetchById(workspaceSlug, pageId);
      runInAction(() => {
        if (page?.id) {
          const pageInstance = this.getPageById(page.id);
          if (pageInstance) pageInstance.mutateProperties(page, false);
          else set(this.data, [page.id], new WikiPage(this.store, page));
        }
        this.loader = undefined;
      });
      if (page?.access === 1) await this.fetchShares(workspaceSlug, pageId);
      return page;
    } catch (error) {
      runInAction(() => {
        this.loader = undefined;
        this.error = { title: "Failed", description: "Failed to fetch the page, please try again later." };
      });
      throw error;
    }
  };

  createPage = async (pageData: Partial<TPage>) => {
    const { workspaceSlug } = this.store.router;
    if (!workspaceSlug) return undefined;
    const page = await this.service.create(workspaceSlug, pageData);
    runInAction(() => {
      if (page?.id) set(this.data, [page.id], new WikiPage(this.store, page));
    });
    return page;
  };

  removePage = async ({ pageId }: { pageId: string }) => {
    const { workspaceSlug } = this.store.router;
    if (!workspaceSlug || !pageId) return undefined;
    await this.service.remove(workspaceSlug, pageId);
    runInAction(() => {
      unset(this.data, [pageId]);
      this.treeNodes = this.treeNodes.filter((node) => node.id !== pageId);
    });
  };

  restoreArchivedPage = async (workspaceSlug: string, pageId: string) => {
    await this.service.restore(workspaceSlug, pageId);
    runInAction(() => {
      this.treeNodes = this.treeNodes.map((node) => (node.id === pageId ? { ...node, archived_at: null } : node));
      const page = this.data[pageId];
      if (page) page.mutateProperties({ archived_at: null }, false);
    });
  };

  fetchShares = async (workspaceSlug: string, pageId: string) => {
    const shares = await this.service.fetchShares(workspaceSlug, pageId);
    runInAction(() => {
      set(this.shares, [pageId], shares);
    });
    return shares;
  };

  createShare = async (workspaceSlug: string, pageId: string, data: Partial<TPageShare>) => {
    const share = await this.service.createShare(workspaceSlug, pageId, data);
    runInAction(() => {
      set(this.shares, [pageId], [...(this.shares[pageId] ?? []), share]);
    });
  };

  updateShare = async (workspaceSlug: string, pageId: string, shareId: string, data: Partial<TPageShare>) => {
    const share = await this.service.updateShare(workspaceSlug, shareId, data);
    runInAction(() => {
      set(
        this.shares,
        [pageId],
        (this.shares[pageId] ?? []).map((existing) => (existing.id === shareId ? share : existing))
      );
    });
  };

  deleteShare = async (workspaceSlug: string, pageId: string, shareId: string) => {
    await this.service.deleteShare(workspaceSlug, shareId);
    runInAction(() => {
      set(
        this.shares,
        [pageId],
        (this.shares[pageId] ?? []).filter((existing) => existing.id !== shareId)
      );
    });
  };

  fetchComments = async (workspaceSlug: string, pageId: string) => {
    const comments = await this.service.fetchComments(workspaceSlug, pageId);
    runInAction(() => {
      set(this.comments, [pageId], comments);
    });
    return comments;
  };

  createComment = async (workspaceSlug: string, pageId: string, data: Partial<TPageComment>) => {
    const comment = await this.service.createComment(workspaceSlug, pageId, data);
    runInAction(() => {
      set(this.comments, [pageId], [...(this.comments[pageId] ?? []), comment]);
    });
  };

  updateComment = async (workspaceSlug: string, pageId: string, commentId: string, data: Partial<TPageComment>) => {
    const comment = await this.service.updateComment(workspaceSlug, commentId, data);
    runInAction(() => {
      set(
        this.comments,
        [pageId],
        (this.comments[pageId] ?? []).map((existing) => (existing.id === commentId ? comment : existing))
      );
    });
  };

  deleteComment = async (workspaceSlug: string, pageId: string, commentId: string) => {
    await this.service.deleteComment(workspaceSlug, commentId);
    runInAction(() => {
      set(
        this.comments,
        [pageId],
        (this.comments[pageId] ?? []).filter((existing) => existing.id !== commentId)
      );
    });
  };
}
