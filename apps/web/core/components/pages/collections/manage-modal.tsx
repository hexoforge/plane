/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import { Check, Pencil, Plus, Trash2, X } from "lucide-react";
// plane imports
import { Button } from "@plane/propel/button";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { AlertModalCore, EModalPosition, EModalWidth, Input, ModalCore } from "@plane/ui";
// hooks
import { useProjectPageCollections } from "@/hooks/store";

type Props = {
  isOpen: boolean;
  onClose: () => void;
  workspaceSlug: string;
  projectId: string;
};

export const ManageCollectionsModal = observer(function ManageCollectionsModal(props: Props) {
  const { isOpen, onClose, workspaceSlug, projectId } = props;
  // states
  const [newCollectionName, setNewCollectionName] = useState("");
  const [isCreating, setIsCreating] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingName, setEditingName] = useState("");
  const [deletingId, setDeletingId] = useState<string | null>(null);
  // store hooks
  const { getCollectionById, getCollectionIdsByProject, createCollection, updateCollection, removeCollection } =
    useProjectPageCollections();
  // derived values
  const collectionIds = getCollectionIdsByProject(projectId);

  const handleCreate = async () => {
    const name = newCollectionName.trim();
    if (!name) return;
    setIsCreating(true);
    try {
      await createCollection(workspaceSlug, projectId, { name, project: projectId });
      setNewCollectionName("");
    } catch (error) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: "Error!",
        message: (error as { error?: string })?.error || "Collection could not be created.",
      });
    } finally {
      setIsCreating(false);
    }
  };

  const startRename = (collectionId: string, currentName: string) => {
    setEditingId(collectionId);
    setEditingName(currentName);
  };

  const handleRename = async (collectionId: string) => {
    const name = editingName.trim();
    if (!name) return;
    try {
      await updateCollection(workspaceSlug, projectId, collectionId, { name });
      setEditingId(null);
    } catch (error) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: "Error!",
        message: (error as { error?: string })?.error || "Collection could not be renamed.",
      });
    }
  };

  const handleDelete = async () => {
    if (!deletingId) return;
    try {
      await removeCollection(workspaceSlug, projectId, deletingId);
      setDeletingId(null);
    } catch (error) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: "Error!",
        message: (error as Error)?.message || "Collection could not be deleted.",
      });
    }
  };

  return (
    <>
      <AlertModalCore
        isOpen={!!deletingId}
        handleClose={() => setDeletingId(null)}
        handleSubmit={handleDelete}
        isSubmitting={false}
        title="Delete collection"
        content="Are you sure you want to delete this collection? Pages inside it will move to General. This action cannot be undone."
      />
      <ModalCore isOpen={isOpen} handleClose={onClose} position={EModalPosition.TOP} width={EModalWidth.XL}>
        <div className="space-y-3 p-5">
          <h3 className="text-lg font-medium text-primary">Manage collections</h3>
          <div className="space-y-1">
            {collectionIds.map((collectionId) => {
              const collection = getCollectionById(collectionId);
              if (!collection) return null;
              const isEditing = editingId === collectionId;
              return (
                <div
                  key={collectionId}
                  className="flex items-center gap-2 rounded-md px-2 py-1.5 hover:bg-layer-transparent-hover"
                >
                  {isEditing ? (
                    <>
                      <Input
                        value={editingName}
                        onChange={(e) => setEditingName(e.target.value)}
                        className="flex-1"
                        inputSize="xs"
                      />
                      <button onClick={() => handleRename(collectionId)} className="text-secondary hover:text-primary">
                        <Check className="size-4" />
                      </button>
                      <button onClick={() => setEditingId(null)} className="text-secondary hover:text-primary">
                        <X className="size-4" />
                      </button>
                    </>
                  ) : (
                    <>
                      <span className="text-sm flex-1 truncate text-primary">{collection.name}</span>
                      <button
                        onClick={() => startRename(collectionId, collection.name)}
                        className="text-secondary hover:text-primary"
                        aria-label={`Rename ${collection.name}`}
                      >
                        <Pencil className="size-3.5" />
                      </button>
                      {!collection.is_default && (
                        <button
                          onClick={() => setDeletingId(collectionId)}
                          className="hover:text-danger-text text-secondary"
                          aria-label={`Delete ${collection.name}`}
                        >
                          <Trash2 className="size-3.5" />
                        </button>
                      )}
                    </>
                  )}
                </div>
              );
            })}
          </div>
          <div className="flex items-center gap-2 border-t border-subtle pt-3">
            <Input
              value={newCollectionName}
              onChange={(e) => setNewCollectionName(e.target.value)}
              placeholder="New collection name"
              className="flex-1"
              inputSize="sm"
              onKeyDown={(e) => {
                if (e.key === "Enter") handleCreate();
              }}
            />
            <Button variant="secondary" size="sm" onClick={handleCreate} loading={isCreating}>
              <Plus className="size-3.5" />
              Add
            </Button>
          </div>
        </div>
      </ModalCore>
    </>
  );
});
