/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useContext } from "react";
// context
import { StoreContext } from "@/lib/store-context";
// mobx store
import type { IProjectPageStore } from "@/store/pages/project-page.store";
import type { IWikiStore } from "@/store/wiki/wiki.store";

export enum EPageStoreType {
  PROJECT = "PROJECT_PAGE",
  WIKI = "WIKI_PAGE",
}

export type TReturnType = {
  [EPageStoreType.PROJECT]: IProjectPageStore;
  [EPageStoreType.WIKI]: IWikiStore;
};

export const usePageStore = <T extends EPageStoreType>(storeType: T): TReturnType[T] => {
  const context = useContext(StoreContext);
  if (context === undefined) throw new Error("usePageStore must be used within StoreProvider");

  if (storeType === EPageStoreType.PROJECT) {
    return context.projectPages as TReturnType[T];
  }
  if (storeType === EPageStoreType.WIKI) {
    return context.wiki as TReturnType[T];
  }

  throw new Error(`Invalid store type: ${storeType}`);
};
