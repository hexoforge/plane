/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import Link from "next/link";
import { ArchiveRestoreIcon } from "lucide-react";
// plane imports
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { ArchiveIcon, ChevronRightIcon } from "@plane/propel/icons";
import { IconButton } from "@plane/propel/icon-button";
import { cn } from "@plane/utils";
// hooks
import { EPageStoreType, usePageStore } from "@/hooks/store";

type Props = {
  workspaceSlug: string;
};

export const WikiArchivedSection = observer(function WikiArchivedSection(props: Props) {
  const { workspaceSlug } = props;
  const [isOpen, setIsOpen] = useState(false);
  const { getArchivedPageNodes, restoreArchivedPage } = usePageStore(EPageStoreType.WIKI);
  const archivedNodes = getArchivedPageNodes();

  const handleRestore = async (pageId: string) => {
    try {
      await restoreArchivedPage(workspaceSlug, pageId);
      setToast({ type: TOAST_TYPE.SUCCESS, title: "Success!", message: "Page restored successfully." });
    } catch {
      setToast({ type: TOAST_TYPE.ERROR, title: "Error!", message: "Page could not be restored." });
    }
  };

  return (
    <div className="mt-2 border-t border-subtle pt-2">
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        className="flex w-full items-center gap-1.5 rounded-md px-2 py-1 text-13 font-medium text-tertiary hover:bg-layer-transparent-hover"
      >
        <ChevronRightIcon className={cn("size-3 flex-shrink-0 transition-transform", { "rotate-90": isOpen })} />
        <ArchiveIcon className="size-3.5 flex-shrink-0" />
        <span>Archived</span>
        <span className="ml-auto text-placeholder">{archivedNodes.length}</span>
      </button>
      {isOpen && (
        <div>
          {archivedNodes.length === 0 ? (
            <p className="py-1 pl-8 text-12 text-placeholder">No archived pages</p>
          ) : (
            archivedNodes.map((node) => (
              <div
                key={node.id}
                className="group/archived-item flex items-center gap-1.5 rounded-md py-1 pr-2 pl-8 text-13 text-secondary hover:bg-layer-transparent-hover"
              >
                <Link href={`/${workspaceSlug}/wiki/${node.id}`} className="min-w-0 flex-1 truncate">
                  {node.name?.trim() || "Untitled"}
                </Link>
                <IconButton
                  variant="ghost"
                  size="sm"
                  icon={ArchiveRestoreIcon}
                  onClick={() => handleRestore(node.id)}
                  className="flex-shrink-0 opacity-0 group-hover/archived-item:opacity-100"
                  aria-label="Restore page"
                />
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
});
