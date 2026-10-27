/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { Folder } from "lucide-react";
// plane imports
import { CheckIcon } from "@plane/propel/icons";
import { CustomMenu } from "@plane/ui";
// hooks
import { useProjectPageCollections } from "@/hooks/store";
// store
import type { TPageInstance } from "@/store/pages/base-page";

type Props = {
  page: TPageInstance;
  projectId: string;
};

export const PageCollectionSelect = observer(function PageCollectionSelect(props: Props) {
  const { page, projectId } = props;
  // store hooks
  const { getCollectionById, getCollectionIdsByProject, getDefaultCollectionId } = useProjectPageCollections();
  // derived values
  const collectionIds = getCollectionIdsByProject(projectId);
  const defaultCollectionId = getDefaultCollectionId(projectId);
  const currentCollectionId = page.collection ?? defaultCollectionId;
  const currentCollection = currentCollectionId ? getCollectionById(currentCollectionId) : undefined;

  if (collectionIds.length <= 1) return null;

  return (
    <CustomMenu
      customButton={
        <div className="flex items-center gap-1 text-tertiary hover:text-secondary">
          <Folder className="size-3.5" />
          <span className="text-xs">{currentCollection?.name ?? "General"}</span>
        </div>
      }
      placement="bottom-end"
      maxHeight="lg"
      closeOnSelect
    >
      {collectionIds.map((collectionId) => {
        const collection = getCollectionById(collectionId);
        if (!collection) return null;
        return (
          <CustomMenu.MenuItem
            key={collectionId}
            className="flex items-center justify-between gap-2"
            onClick={(e) => {
              e.preventDefault();
              page.update({ collection: collectionId });
            }}
          >
            <span className="truncate">{collection.name}</span>
            {currentCollectionId === collectionId && <CheckIcon className="size-3 shrink-0" />}
          </CustomMenu.MenuItem>
        );
      })}
    </CustomMenu>
  );
});
