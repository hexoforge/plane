/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useRef, useState } from "react";
import { observer } from "mobx-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ChevronRight, Plus } from "lucide-react";
// plane imports
import { Logo } from "@plane/propel/emoji-icon-picker";
import { PageIcon } from "@plane/propel/icons";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { FavoriteStar } from "@plane/ui";
import type { TPageTreeNode } from "@plane/utils";
import { cn, getPageName } from "@plane/utils";
// hooks
import { useAppRouter } from "@/hooks/use-app-router";
import { usePageOperations } from "@/hooks/use-page-operations";
// plane web hooks
import type { EPageStoreType } from "@/hooks/store";
import { usePage, usePageStore } from "@/hooks/store";
// store
import type { TPageInstance } from "@/store/pages/base-page";
// local imports
import { PageActions } from "../dropdowns";

type Props = {
  node: TPageTreeNode;
  storeType: EPageStoreType;
  collectionId: string | undefined;
  depth: number;
};

export const PageTreeNode = observer(function PageTreeNode(props: Props) {
  const { node, storeType, collectionId, depth } = props;
  // store hooks
  const page = usePage({ pageId: node.id, storeType });

  if (!page) return null;

  return <PageTreeNodeRow node={node} page={page} storeType={storeType} collectionId={collectionId} depth={depth} />;
});

type TRowProps = {
  node: TPageTreeNode;
  page: TPageInstance;
  storeType: EPageStoreType;
  collectionId: string | undefined;
  depth: number;
};

const PageTreeNodeRow = observer(function PageTreeNodeRow(props: TRowProps) {
  const { node, page, storeType, collectionId, depth } = props;
  // refs
  const parentRef = useRef(null);
  // states
  const [isExpanded, setIsExpanded] = useState(true);
  const [isCreatingChild, setIsCreatingChild] = useState(false);
  // router
  const router = useAppRouter();
  const { workspaceSlug, projectId } = useParams();
  // store hooks
  const { createPage } = usePageStore(storeType);
  const { pageOperations } = usePageOperations({ page });
  // derived values
  const { name, logo_props, access, is_favorite, canCurrentUserFavoritePage, getRedirectionLink } = page;
  const hasChildren = node.children.length > 0;

  const handleCreateChild = async (e: React.MouseEvent) => {
    e.preventDefault();
    setIsCreatingChild(true);
    try {
      const childPage = await createPage({ parent: node.id, collection: collectionId, access });
      setIsExpanded(true);
      if (childPage) router.push(`/${workspaceSlug}/projects/${projectId}/pages/${childPage.id}`);
    } catch (_error) {
      setToast({ type: TOAST_TYPE.ERROR, title: "Error!", message: "Page could not be created." });
    } finally {
      setIsCreatingChild(false);
    }
  };

  return (
    <div>
      <div
        ref={parentRef}
        className="group flex items-center gap-1 rounded-md py-1 pr-2 hover:bg-layer-transparent-hover"
        style={{ paddingLeft: `${depth * 16 + 4}px` }}
      >
        <button
          type="button"
          onClick={() => setIsExpanded((prev) => !prev)}
          aria-label={isExpanded ? "Collapse sub-pages" : "Expand sub-pages"}
          className={cn(
            "grid size-5 shrink-0 place-items-center rounded-sm text-tertiary hover:bg-layer-transparent-hover",
            { invisible: !hasChildren }
          )}
        >
          <ChevronRight className={cn("size-3.5 transition-transform", { "rotate-90": isExpanded })} />
        </button>
        {logo_props?.in_use ? (
          <Logo logo={logo_props} size={14} type="lucide" />
        ) : (
          <PageIcon className="size-3.5 shrink-0 text-tertiary" />
        )}
        <Link href={getRedirectionLink()} className="flex-1 truncate text-13 text-primary">
          {getPageName(name)}
        </Link>
        <div className="flex shrink-0 items-center gap-1 opacity-0 group-hover:opacity-100">
          <button
            type="button"
            onClick={handleCreateChild}
            disabled={isCreatingChild}
            className="grid size-5 place-items-center rounded-sm text-tertiary hover:bg-layer-transparent-hover"
            aria-label="Add sub-page"
          >
            <Plus className="size-3.5" />
          </button>
          {canCurrentUserFavoritePage && (
            <FavoriteStar
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                pageOperations.toggleFavorite();
              }}
              selected={is_favorite}
            />
          )}
          <PageActions
            optionsOrder={[
              "open-in-new-tab",
              "copy-link",
              "make-a-copy",
              "toggle-access",
              "share",
              "archive-restore",
              "delete",
            ]}
            page={page}
            parentRef={parentRef}
            storeType={storeType}
          />
        </div>
      </div>
      {isExpanded && hasChildren && (
        <div>
          {node.children.map((child) => (
            <PageTreeNode
              key={child.id}
              node={child}
              storeType={storeType}
              collectionId={collectionId}
              depth={depth + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
});
