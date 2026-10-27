/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { computed, makeObservable } from "mobx";
// constants
import { EPageAccess, EUserPermissions } from "@plane/constants";
import type { TPage } from "@plane/types";
// store
import type { RootStore } from "@/store/root.store";
import { WikiService } from "@/services/wiki.service";
import { BasePage } from "./base-page";
import type { TPageInstance } from "./base-page";

const wikiService = new WikiService();

export type TWikiPage = TPageInstance;

export class WikiPage extends BasePage implements TWikiPage {
  constructor(store: RootStore, page: TPage) {
    const { workspaceSlug } = store.router;

    super(store, page, {
      update: async (payload) => {
        if (!workspaceSlug || !page.id) throw new Error("Missing required fields.");
        return await wikiService.update(workspaceSlug, page.id, payload);
      },
      updateDescription: async (document) => {
        if (!workspaceSlug || !page.id) throw new Error("Missing required fields.");
        await wikiService.updateDescription(workspaceSlug, page.id, document);
      },
      updateAccess: async (payload) => {
        if (!workspaceSlug || !page.id) throw new Error("Missing required fields.");
        await wikiService.update(workspaceSlug, page.id, payload);
      },
      lock: async () => {
        throw new Error("Locking is not supported for wiki pages.");
      },
      unlock: async () => {
        throw new Error("Locking is not supported for wiki pages.");
      },
      archive: async () => {
        if (!workspaceSlug || !page.id) throw new Error("Missing required fields.");
        return await wikiService.archive(workspaceSlug, page.id);
      },
      restore: async () => {
        if (!workspaceSlug || !page.id) throw new Error("Missing required fields.");
        await wikiService.restore(workspaceSlug, page.id);
      },
      duplicate: async () => {
        throw new Error("Duplicating is not supported for wiki pages.");
      },
    });

    makeObservable(this, {
      canCurrentUserAccessPage: computed,
      canCurrentUserEditPage: computed,
      canCurrentUserDuplicatePage: computed,
      canCurrentUserLockPage: computed,
      canCurrentUserChangeAccess: computed,
      canCurrentUserArchivePage: computed,
      canCurrentUserDeletePage: computed,
      canCurrentUserFavoritePage: computed,
      canCurrentUserMovePage: computed,
      isContentEditable: computed,
    });
  }

  private get workspaceRole(): EUserPermissions | undefined {
    const { workspaceSlug } = this.rootStore.router;
    if (!workspaceSlug) return undefined;
    return this.rootStore.user.permission.getWorkspaceRoleByWorkspaceSlug(workspaceSlug.toString()) as
      | EUserPermissions
      | undefined;
  }

  private get currentUserShareRole() {
    if (!this.id) return undefined;
    return this.rootStore.wiki.getCurrentUserShareRole(this.id);
  }

  get canCurrentUserAccessPage() {
    const isPagePublic = this.access === EPageAccess.PUBLIC;
    return isPagePublic || this.isCurrentUserOwner || this.currentUserShareRole !== undefined;
  }

  get canCurrentUserEditPage() {
    const isPagePublic = this.access === EPageAccess.PUBLIC;
    if (this.isCurrentUserOwner) return true;
    if (isPagePublic) return !!this.workspaceRole && this.workspaceRole >= EUserPermissions.MEMBER;
    return this.currentUserShareRole === 2;
  }

  get canCurrentUserDuplicatePage() {
    return false;
  }

  get canCurrentUserLockPage() {
    return false;
  }

  get canCurrentUserChangeAccess() {
    return this.isCurrentUserOwner || this.workspaceRole === EUserPermissions.ADMIN;
  }

  get canCurrentUserArchivePage() {
    return this.isCurrentUserOwner || this.workspaceRole === EUserPermissions.ADMIN;
  }

  get canCurrentUserDeletePage() {
    return this.isCurrentUserOwner || this.workspaceRole === EUserPermissions.ADMIN;
  }

  get canCurrentUserFavoritePage() {
    return !!this.workspaceRole && this.workspaceRole >= EUserPermissions.MEMBER;
  }

  get canCurrentUserMovePage() {
    return false;
  }

  get isContentEditable() {
    const isArchived = this.archived_at;
    return !isArchived && this.canCurrentUserEditPage;
  }

  getRedirectionLink = () => {
    const { workspaceSlug } = this.rootStore.router;
    return `/${workspaceSlug}/wiki/${this.id}`;
  };
}
