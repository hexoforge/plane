/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { Plus } from "lucide-react";
// plane imports
import { Logo } from "@plane/propel/emoji-icon-picker";
import { ChevronRightIcon, LockIcon, PageIcon } from "@plane/propel/icons";
import { IconButton } from "@plane/propel/icon-button";
import { cn } from "@plane/utils";
// hooks
import { EPageStoreType, usePageStore } from "@/hooks/store";

type Props = {
  pageId: string;
  collectionId: string;
  depth: number;
  workspaceSlug: string;
  expandedIds: Set<string>;
  onToggleExpand: (id: string) => void;
  visibleIds: Set<string> | null;
  onCreateSubPage: (collectionId: string, parentId: string) => void;
};

export const WikiPageTreeNode = observer(function WikiPageTreeNode(props: Props) {
  const { pageId, collectionId, depth, workspaceSlug, expandedIds, onToggleExpand, visibleIds, onCreateSubPage } =
    props;
  const { pageId: activePageId } = useParams();
  const { getChildPageIds } = usePageStore(EPageStoreType.WIKI);
  const wikiStore = usePageStore(EPageStoreType.WIKI);
  const node = wikiStore.treeNodes.find((item) => item.id === pageId);

  if (!node) return null;

  const childIds = getChildPageIds(collectionId, pageId).filter((id) => !visibleIds || visibleIds.has(id));
  const hasChildren = childIds.length > 0;
  const isExpanded = expandedIds.has(pageId);
  const isActive = activePageId === pageId;

  return (
    <div>
      <div
        className={cn(
          "group/wiki-node relative flex items-center gap-1 rounded-md px-2 py-1 text-13 text-secondary hover:bg-layer-transparent-hover",
          { "bg-layer-transparent-selected text-primary": isActive }
        )}
        style={{ paddingLeft: `${depth * 14 + 8}px` }}
      >
        <button
          type="button"
          onClick={() => onToggleExpand(pageId)}
          className={cn("grid size-4 flex-shrink-0 place-items-center rounded-sm text-placeholder", {
            invisible: !hasChildren,
          })}
          aria-label={isExpanded ? "Collapse" : "Expand"}
        >
          <ChevronRightIcon className={cn("size-3 transition-transform", { "rotate-90": isExpanded })} />
        </button>
        <Link href={`/${workspaceSlug}/wiki/${pageId}`} className="flex min-w-0 flex-1 items-center gap-1.5">
          <span className="grid size-4 flex-shrink-0 place-items-center">
            {node.logo_props?.in_use ? (
              <Logo logo={node.logo_props} size={14} />
            ) : (
              <PageIcon className="size-3.5 text-tertiary" />
            )}
          </span>
          <span className="truncate">{node.name?.trim() || "Untitled"}</span>
          {node.access === 1 && <LockIcon className="size-3 flex-shrink-0 text-placeholder" />}
        </Link>
        <IconButton
          variant="ghost"
          size="sm"
          icon={Plus}
          onClick={() => onCreateSubPage(collectionId, pageId)}
          className="flex-shrink-0 opacity-0 group-hover/wiki-node:opacity-100"
          aria-label="Add sub-page"
        />
      </div>
      {hasChildren && isExpanded && (
        <div>
          {childIds.map((childId) => (
            <WikiPageTreeNode
              key={childId}
              pageId={childId}
              collectionId={collectionId}
              depth={depth + 1}
              workspaceSlug={workspaceSlug}
              expandedIds={expandedIds}
              onToggleExpand={onToggleExpand}
              visibleIds={visibleIds}
              onCreateSubPage={onCreateSubPage}
            />
          ))}
        </div>
      )}
    </div>
  );
});
