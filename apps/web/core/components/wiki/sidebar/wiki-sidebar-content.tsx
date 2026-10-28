/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useMemo } from "react";
import { observer } from "mobx-react";
import useSWR from "swr";
// plane imports
import type { TPageCollection } from "@plane/types";
import { Loader } from "@plane/ui";
// components
import { SimpleEmptyState } from "@/components/empty-state/simple-empty-state-root";
// hooks
import { EPageStoreType, usePageStore } from "@/hooks/store";
// local imports
import { WikiArchivedSection } from "./archived-section";
import { WikiCollectionSection } from "./collection-section";

type Props = {
  workspaceSlug: string;
  visibleIds: Set<string> | null;
  expandedIds: Set<string>;
  onToggleExpand: (id: string) => void;
  onCreatePage: (collectionId: string, parentId: string | null) => void;
  onDeleteCollection: (collection: TPageCollection) => void;
};

export const WikiSidebarContent = observer(function WikiSidebarContent(props: Props) {
  const { workspaceSlug, visibleIds, expandedIds, onToggleExpand, onCreatePage, onDeleteCollection } = props;
  const { collections, collectionIds, loader, error, canCurrentUserCreatePage, fetchTree } = usePageStore(
    EPageStoreType.WIKI
  );

  const { isLoading } = useSWR(workspaceSlug ? `WIKI_TREE_${workspaceSlug}` : null, () =>
    workspaceSlug ? fetchTree(workspaceSlug) : undefined
  );

  const sortedCollections = useMemo(
    () => collectionIds.map((id) => collections[id]).sort((a, b) => a.sort_order - b.sort_order),
    [collectionIds, collections]
  );

  return (
    <div className="flex-1 overflow-y-auto px-2 py-2">
      {isLoading && loader === "init-loader" ? (
        <Loader className="space-y-2 px-2">
          <Loader.Item height="28px" />
          <Loader.Item height="28px" />
          <Loader.Item height="28px" width="80%" />
        </Loader>
      ) : error ? (
        <div className="px-2 py-4">
          <SimpleEmptyState title={error.title} description={error.description} />
        </div>
      ) : sortedCollections.length === 0 ? (
        <div className="px-2 py-4">
          <SimpleEmptyState
            title="No collections yet"
            description={
              canCurrentUserCreatePage ? "Create a collection to start organizing wiki pages." : "No wiki pages yet."
            }
          />
        </div>
      ) : (
        <div className="flex flex-col gap-1">
          {sortedCollections.map((collection) => (
            <WikiCollectionSection
              key={collection.id}
              collection={collection}
              workspaceSlug={workspaceSlug}
              visibleIds={visibleIds}
              expandedIds={expandedIds}
              onToggleExpand={onToggleExpand}
              onCreatePage={onCreatePage}
              onDeleteCollection={onDeleteCollection}
            />
          ))}
        </div>
      )}
      {!isLoading && !error && <WikiArchivedSection workspaceSlug={workspaceSlug} />}
    </div>
  );
});
