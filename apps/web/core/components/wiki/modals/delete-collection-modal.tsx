/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
// plane imports
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import type { TPageCollection } from "@plane/types";
import { AlertModalCore } from "@plane/ui";
// hooks
import { EPageStoreType, usePageStore } from "@/hooks/store";

type Props = {
  workspaceSlug: string;
  collection: TPageCollection | null;
  isOpen: boolean;
  onClose: () => void;
};

export function DeleteWikiCollectionModal(props: Props) {
  const { workspaceSlug, collection, isOpen, onClose } = props;
  const [isDeleting, setIsDeleting] = useState(false);
  const { deleteCollection } = usePageStore(EPageStoreType.WIKI);

  const handleDelete = async () => {
    if (!collection) return;
    setIsDeleting(true);
    try {
      await deleteCollection(workspaceSlug, collection.id);
      onClose();
      setToast({ type: TOAST_TYPE.SUCCESS, title: "Success!", message: "Collection deleted successfully." });
    } catch {
      setToast({ type: TOAST_TYPE.ERROR, title: "Error!", message: "Collection could not be deleted." });
    } finally {
      setIsDeleting(false);
    }
  };

  if (!collection) return null;

  return (
    <AlertModalCore
      handleClose={onClose}
      handleSubmit={handleDelete}
      isSubmitting={isDeleting}
      isOpen={isOpen}
      title="Delete collection"
      content={
        <>
          Are you sure you want to delete <span className="font-medium text-primary">{collection.name}</span>? Pages
          inside it will no longer belong to a collection. This action cannot be undone.
        </>
      }
    />
  );
}
