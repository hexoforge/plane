/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import { MoreHorizontal, Plus } from "lucide-react";
// plane imports
import { ChevronRightIcon, LockIcon, TrashIcon } from "@plane/propel/icons";
import { IconButton } from "@plane/propel/icon-button";
import type { TPageCollection } from "@plane/types";
import { CustomMenu } from "@plane/ui";
import { cn } from "@plane/utils";
// hooks
import { EPageStoreType, usePageStore } from "@/hooks/store";
// local imports
import { WikiPageTreeNode } from "./page-tree-node";

type Props = {
  collection: TPageCollection;
  workspaceSlug: string;
  visibleIds: Set<string> | null;
  expandedIds: Set<string>;
  onToggleExpand: (id: string) => void;
  onCreatePage: (collectionId: string, parentId: string | null) => void;
  onDeleteCollection: (collection: TPageCollection) => void;
};

export const WikiCollectionSection = observer(function WikiCollectionSection(props: Props) {
  const { collection, workspaceSlug, visibleIds, expandedIds, onToggleExpand, onCreatePage, onDeleteCollection } =
    props;
  const [isOpen, setIsOpen] = useState(true);
  const { getChildPageIds } = usePageStore(EPageStoreType.WIKI);

  const rootPageIds = getChildPageIds(collection.id, null).filter((id) => !visibleIds || visibleIds.has(id));
  const canDelete = !collection.is_default;

  if (visibleIds && rootPageIds.length === 0) return null;

  return (
    <div className="flex flex-col">
      <div className="group/wiki-collection flex items-center gap-1 rounded-md px-2 py-1 text-13 font-medium text-tertiary hover:bg-layer-transparent-hover">
        <button
          type="button"
          onClick={() => setIsOpen((prev) => !prev)}
          className="grid size-4 flex-shrink-0 place-items-center rounded-sm"
          aria-label={isOpen ? "Collapse collection" : "Expand collection"}
        >
          <ChevronRightIcon className={cn("size-3 transition-transform", { "rotate-90": isOpen })} />
        </button>
        <span className="flex min-w-0 flex-1 items-center gap-1.5 truncate">
          {collection.name}
          {collection.access === 1 && <LockIcon className="size-3 flex-shrink-0 text-placeholder" />}
        </span>
        <IconButton
          variant="ghost"
          size="sm"
          icon={Plus}
          onClick={() => onCreatePage(collection.id, null)}
          className="flex-shrink-0 opacity-0 group-hover/wiki-collection:opacity-100"
          aria-label="Add page"
        />
        {canDelete && (
          <CustomMenu
            customButton={
              <IconButton
                variant="ghost"
                size="sm"
                icon={MoreHorizontal}
                className="flex-shrink-0 opacity-0 group-hover/wiki-collection:opacity-100"
              />
            }
            placement="bottom-end"
            closeOnSelect
            ariaLabel="Collection options"
          >
            <CustomMenu.MenuItem onClick={() => onDeleteCollection(collection)}>
              <span className="flex items-center gap-2 text-danger-primary">
                <TrashIcon className="size-3.5" />
                Delete collection
              </span>
            </CustomMenu.MenuItem>
          </CustomMenu>
        )}
      </div>
      {isOpen && (
        <div>
          {rootPageIds.length === 0 ? (
            <p className="py-1 pl-8 text-12 text-placeholder">No pages yet</p>
          ) : (
            rootPageIds.map((pageId) => (
              <WikiPageTreeNode
                key={pageId}
                pageId={pageId}
                collectionId={collection.id}
                depth={1}
                workspaceSlug={workspaceSlug}
                expandedIds={expandedIds}
                onToggleExpand={onToggleExpand}
                visibleIds={visibleIds}
                onCreateSubPage={onCreatePage}
              />
            ))
          )}
        </div>
      )}
    </div>
  );
});
