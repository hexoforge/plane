/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import { ChevronDown, Folder, Settings } from "lucide-react";
// plane imports
import { getButtonStyling } from "@plane/propel/button";
import { CheckIcon } from "@plane/propel/icons";
import { CustomMenu } from "@plane/ui";
// hooks
import { useProjectPageCollections } from "@/hooks/store";
// local imports
import { ManageCollectionsModal } from "./manage-modal";

type Props = {
  workspaceSlug: string;
  projectId: string;
  activeCollectionId: string | null;
  onChange: (collectionId: string | null) => void;
};

export const PageCollectionSwitcher = observer(function PageCollectionSwitcher(props: Props) {
  const { workspaceSlug, projectId, activeCollectionId, onChange } = props;
  // states
  const [isManageModalOpen, setIsManageModalOpen] = useState(false);
  // store hooks
  const { getCollectionById, getCollectionIdsByProject, getDefaultCollectionId, canCurrentUserManageCollections } =
    useProjectPageCollections();
  // derived values
  const collectionIds = getCollectionIdsByProject(projectId);
  const defaultCollectionId = getDefaultCollectionId(projectId);
  const selectedCollectionId = activeCollectionId ?? defaultCollectionId;
  const selectedCollection = selectedCollectionId ? getCollectionById(selectedCollectionId) : undefined;

  return (
    <>
      <ManageCollectionsModal
        isOpen={isManageModalOpen}
        onClose={() => setIsManageModalOpen(false)}
        workspaceSlug={workspaceSlug}
        projectId={projectId}
      />
      <CustomMenu
        customButton={
          <div className={getButtonStyling("secondary", "lg")}>
            <Folder className="size-3" />
            {selectedCollection?.name ?? "General"}
            <ChevronDown className="size-3" />
          </div>
        }
        placement="bottom-start"
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
              onClick={() => onChange(collectionId === defaultCollectionId ? null : collectionId)}
            >
              <span className="truncate">{collection.name}</span>
              {selectedCollectionId === collectionId && <CheckIcon className="size-3 shrink-0" />}
            </CustomMenu.MenuItem>
          );
        })}
        {canCurrentUserManageCollections && (
          <>
            <hr className="my-2 border-subtle" />
            <CustomMenu.MenuItem className="flex items-center gap-2" onClick={() => setIsManageModalOpen(true)}>
              <Settings className="size-3" />
              Manage collections
            </CustomMenu.MenuItem>
          </>
        )}
      </CustomMenu>
    </>
  );
});
