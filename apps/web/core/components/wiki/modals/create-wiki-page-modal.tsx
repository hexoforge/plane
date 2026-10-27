/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { useRouter } from "next/navigation";
// plane imports
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import type { TPage } from "@plane/types";
import { EModalPosition, EModalWidth, ModalCore } from "@plane/ui";
// components
import { PageForm } from "@/components/pages/modals/page-form";
// hooks
import { EPageStoreType, usePageStore } from "@/hooks/store";

type Props = {
  workspaceSlug: string;
  isOpen: boolean;
  collectionId: string | null;
  parentId: string | null;
  onClose: () => void;
};

export function CreateWikiPageModal(props: Props) {
  const { workspaceSlug, isOpen, collectionId, parentId, onClose } = props;
  const router = useRouter();
  const { createPage } = usePageStore(EPageStoreType.WIKI);
  const [formData, setFormData] = useState<Partial<TPage>>({ name: "" });

  const handleClose = () => {
    setFormData({ name: "" });
    onClose();
  };

  const handleSubmit = async () => {
    try {
      const page = await createPage({ ...formData, collection: collectionId, parent: parentId });
      if (page?.id) {
        handleClose();
        router.push(`/${workspaceSlug}/wiki/${page.id}`);
      }
    } catch (error: any) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: "Error!",
        message: error?.error || "Page could not be created. Please try again.",
      });
    }
  };

  return (
    <ModalCore isOpen={isOpen} handleClose={handleClose} position={EModalPosition.TOP} width={EModalWidth.XXL}>
      <PageForm
        formData={formData}
        handleFormData={(key, value) => setFormData((prev) => ({ ...prev, [key]: value }))}
        handleModalClose={handleClose}
        handleFormSubmit={handleSubmit}
      />
    </ModalCore>
  );
}
