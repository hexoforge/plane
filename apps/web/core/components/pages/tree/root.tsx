/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
// types
import type { TPageNavigationTabs } from "@plane/types";
// helpers
import { buildPageTree, pageBelongsToCollection } from "@plane/utils";
// plane web hooks
import type { EPageStoreType } from "@/hooks/store";
import { usePageStore, useProjectPageCollections } from "@/hooks/store";
// local imports
import { PageTreeNode } from "./tree-node";

type Props = {
  pageType: TPageNavigationTabs;
  storeType: EPageStoreType;
  projectId: string;
  activeCollectionId: string | null;
};

export const PagesTreeRoot = observer(function PagesTreeRoot(props: Props) {
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
  const pagesInCollection = filteredPageIds
    .map((pageId) => getPageById(pageId))
    .filter((page): page is NonNullable<typeof page> => !!page)
    .filter(
      (page) => !collectionId || pageBelongsToCollection(page, collectionId, collectionId === defaultCollectionId)
    );

  const tree = buildPageTree(pagesInCollection);

  if (tree.length === 0)
    return <div className="px-5 py-10 text-center text-13 text-tertiary">No pages in this collection yet.</div>;

  return (
    <div className="flex h-full flex-col gap-0.5 overflow-y-auto px-3 py-3">
      {tree.map((node) => (
        <PageTreeNode key={node.id} node={node} storeType={storeType} collectionId={collectionId} depth={0} />
      ))}
    </div>
  );
});
