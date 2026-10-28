/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import { Plus } from "lucide-react";
// plane imports
import { Button } from "@plane/propel/button";
import type { TPageCollection } from "@plane/types";
// hooks
import { EPageStoreType, usePageStore } from "@/hooks/store";
// local imports
import { CreateWikiCollectionModal } from "../modals/create-collection-modal";
import { CreateWikiPageModal } from "../modals/create-wiki-page-modal";
import { DeleteWikiCollectionModal } from "../modals/delete-collection-modal";
import { useWikiSidebarExpansion } from "./use-wiki-sidebar-expansion";
import { WikiSidebarContent } from "./wiki-sidebar-content";
import { WikiSidebarSearch } from "./wiki-sidebar-search";

type Props = {
  workspaceSlug: string;
};

export const WikiSidebarRoot = observer(function WikiSidebarRoot(props: Props) {
  const { workspaceSlug } = props;
  const [searchQuery, setSearchQuery] = useState("");
  const [isCreateCollectionOpen, setIsCreateCollectionOpen] = useState(false);
  const [pageModalTarget, setPageModalTarget] = useState<{
    collectionId: string | null;
    parentId: string | null;
  } | null>(null);
  const [collectionPendingDelete, setCollectionPendingDelete] = useState<TPageCollection | null>(null);
  const { treeNodes, canCurrentUserCreatePage } = usePageStore(EPageStoreType.WIKI);
  const { expandedIds, toggleExpand, visibleIds } = useWikiSidebarExpansion(searchQuery, treeNodes);

  return (
    <div className="flex h-full w-64 flex-shrink-0 flex-col border-r border-subtle bg-surface-1">
      <CreateWikiCollectionModal
        workspaceSlug={workspaceSlug}
        isOpen={isCreateCollectionOpen}
        onClose={() => setIsCreateCollectionOpen(false)}
      />
      <CreateWikiPageModal
        workspaceSlug={workspaceSlug}
        isOpen={!!pageModalTarget}
        collectionId={pageModalTarget?.collectionId ?? null}
        parentId={pageModalTarget?.parentId ?? null}
        onClose={() => setPageModalTarget(null)}
      />
      <DeleteWikiCollectionModal
        workspaceSlug={workspaceSlug}
        collection={collectionPendingDelete}
        isOpen={!!collectionPendingDelete}
        onClose={() => setCollectionPendingDelete(null)}
      />

      <div className="flex items-center gap-2 border-b border-subtle px-3 py-3">
        <WikiSidebarSearch value={searchQuery} onChange={setSearchQuery} />
        {canCurrentUserCreatePage && (
          <Button variant="secondary" size="sm" onClick={() => setIsCreateCollectionOpen(true)}>
            <Plus className="size-3.5" />
          </Button>
        )}
      </div>

      <WikiSidebarContent
        workspaceSlug={workspaceSlug}
        visibleIds={visibleIds}
        expandedIds={expandedIds}
        onToggleExpand={toggleExpand}
        onCreatePage={(collectionId, parentId) => setPageModalTarget({ collectionId, parentId })}
        onDeleteCollection={setCollectionPendingDelete}
      />
    </div>
  );
});
