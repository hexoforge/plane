/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
// plane imports
import { Button } from "@plane/propel/button";
import { GlobeIcon, LockIcon } from "@plane/propel/icons";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { EModalPosition, EModalWidth, Input, ModalCore } from "@plane/ui";
// components
import { AccessField } from "@/components/common/access-field";
// hooks
import { EPageStoreType, usePageStore } from "@/hooks/store";

type Props = {
  workspaceSlug: string;
  isOpen: boolean;
  onClose: () => void;
};

const ACCESS_SPECIFIERS = [
  { key: 0, i18n_label: "common.access.public", icon: GlobeIcon },
  { key: 1, i18n_label: "common.access.private", icon: LockIcon },
];

export const CreateWikiCollectionModal = observer(function CreateWikiCollectionModal(props: Props) {
  const { workspaceSlug, isOpen, onClose } = props;
  const [name, setName] = useState("");
  const [access, setAccess] = useState<0 | 1>(0);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { createCollection, canCurrentUserCreatePrivateCollection } = usePageStore(EPageStoreType.WIKI);

  const handleClose = () => {
    setName("");
    setAccess(0);
    onClose();
  };

  const handleSubmit = async () => {
    if (!name.trim()) return;
    setIsSubmitting(true);
    try {
      await createCollection(workspaceSlug, { name: name.trim(), access });
      handleClose();
    } catch {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: "Error!",
        message: "Collection could not be created. Please try again.",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <ModalCore isOpen={isOpen} handleClose={handleClose} position={EModalPosition.TOP} width={EModalWidth.XL}>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void handleSubmit();
        }}
      >
        <div className="space-y-4 p-5">
          <h3 className="text-16 font-medium text-primary">New collection</h3>
          <Input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Collection name"
            className="w-full"
            required
          />
          {canCurrentUserCreatePrivateCollection && (
            <AccessField
              onChange={(value) => setAccess(value as 0 | 1)}
              value={access}
              accessSpecifiers={ACCESS_SPECIFIERS}
            />
          )}
        </div>
        <div className="flex items-center justify-end gap-2 border-t-[0.5px] border-subtle px-5 py-4">
          <Button variant="secondary" size="lg" onClick={handleClose} type="button">
            Cancel
          </Button>
          <Button variant="primary" size="lg" type="submit" loading={isSubmitting} disabled={!name.trim()}>
            {isSubmitting ? "Creating" : "Create collection"}
          </Button>
        </div>
      </form>
    </ModalCore>
  );
});
