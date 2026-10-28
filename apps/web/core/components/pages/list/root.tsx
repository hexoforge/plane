/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
// types
import type { TPageNavigationTabs } from "@plane/types";
// helpers
import { pageBelongsToCollection } from "@plane/utils";
// components
import { ListLayout } from "@/components/core/list";
// plane web hooks
import type { EPageStoreType } from "@/hooks/store";
import { usePageStore, useProjectPageCollections } from "@/hooks/store";
// local imports
import { PageListBlock } from "./block";

type TPagesListRoot = {
  pageType: TPageNavigationTabs;
  storeType: EPageStoreType.PROJECT;
  projectId: string;
  activeCollectionId: string | null;
};

export const PagesListRoot = observer(function PagesListRoot(props: TPagesListRoot) {
  const { pageType, storeType, projectId, activeCollectionId } = props;
  // store hooks
  const { getCurrentProjectFilteredPageIdsByTab, getPageById } = usePageStore(storeType);
  const { getDefaultCollectionId } = useProjectPageCollections();
  // derived values
  const filteredPageIds = getCurrentProjectFilteredPageIdsByTab(pageType);
  const defaultCollectionId = getDefaultCollectionId(projectId);
  const collectionId = activeCollectionId ?? defaultCollectionId;

  if (!filteredPageIds) return <></>;

  // collections may not have loaded yet (or none exist for this project), show every page rather than hiding all of them
  const collectionFilteredPageIds = !collectionId
    ? filteredPageIds
    : filteredPageIds.filter((pageId) => {
        const page = getPageById(pageId);
        return !!page && pageBelongsToCollection(page, collectionId, collectionId === defaultCollectionId);
      });

  return (
    <ListLayout>
      {collectionFilteredPageIds.map((pageId) => (
        <PageListBlock key={pageId} pageId={pageId} storeType={storeType} projectId={projectId} />
      ))}
    </ListLayout>
  );
});
