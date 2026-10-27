/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect, useMemo, useState } from "react";
import { observer } from "mobx-react";
import { Plus, Search, X } from "lucide-react";
import useSWR from "swr";
// plane imports
import { Button } from "@plane/propel/button";
import type { TPageCollection } from "@plane/types";
import { Loader } from "@plane/ui";
// components
import { SimpleEmptyState } from "@/components/empty-state/simple-empty-state-root";
// hooks
import { EPageStoreType, usePageStore } from "@/hooks/store";
// local imports
import { CreateWikiCollectionModal } from "../modals/create-collection-modal";
import { CreateWikiPageModal } from "../modals/create-wiki-page-modal";
import { DeleteWikiCollectionModal } from "../modals/delete-collection-modal";
import { WikiArchivedSection } from "./archived-section";
import { WikiCollectionSection } from "./collection-section";

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
  const wikiStore = usePageStore(EPageStoreType.WIKI);
  const { collections, collectionIds, treeNodes, loader, error, canCurrentUserCreatePage, fetchTree } = wikiStore;

  const { isLoading } = useSWR(workspaceSlug ? `WIKI_TREE_${workspaceSlug}` : null, () =>
    workspaceSlug ? fetchTree(workspaceSlug) : undefined
  );

  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());

  const toggleExpand = (id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  // auto-expand ancestors of nodes matching the active search query
  const visibleIds = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    if (!query) return null;
    const byId = new Map(treeNodes.map((node) => [node.id, node]));
    const matched = treeNodes.filter((node) => (node.name ?? "").toLowerCase().includes(query));
    const visible = new Set<string>();
    matched.forEach((node) => {
      let current: typeof node | undefined = node;
      while (current) {
        visible.add(current.id);
        current = current.parent ? byId.get(current.parent) : undefined;
      }
    });
    return visible;
  }, [searchQuery, treeNodes]);

  useEffect(() => {
    if (visibleIds) setExpandedIds(new Set(visibleIds));
  }, [visibleIds]);

  const sortedCollections = useMemo(
    () => collectionIds.map((id) => collections[id]).sort((a, b) => a.sort_order - b.sort_order),
    [collectionIds, collections]
  );

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
        <div className="flex min-w-0 flex-1 items-center gap-2 rounded-md border border-subtle px-2 py-1.5">
          <Search className="size-3.5 flex-shrink-0 text-placeholder" />
          <input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search wiki"
            className="w-full min-w-0 border-none bg-transparent text-13 text-primary placeholder:text-placeholder focus:outline-none"
          />
          {searchQuery && (
            <button type="button" onClick={() => setSearchQuery("")} aria-label="Clear search">
              <X className="size-3.5 text-placeholder" />
            </button>
          )}
        </div>
        {canCurrentUserCreatePage && (
          <Button variant="secondary" size="sm" onClick={() => setIsCreateCollectionOpen(true)}>
            <Plus className="size-3.5" />
          </Button>
        )}
      </div>

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
                onToggleExpand={toggleExpand}
                onCreatePage={(collectionId, parentId) => setPageModalTarget({ collectionId, parentId })}
                onDeleteCollection={(collectionToDelete) => setCollectionPendingDelete(collectionToDelete)}
              />
            ))}
          </div>
        )}
        {!isLoading && !error && <WikiArchivedSection workspaceSlug={workspaceSlug} />}
      </div>
    </div>
  );
});
