/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// plane ui
import { EModalPosition, EModalWidth, ModalCore } from "@plane/ui";

type Props = {
  workspaceSlug: string;
  projectId?: string;
  pageId: string;
  isOpen: boolean;
  onClose: () => void;
};

// placeholder: share management UI is built in feat/wiki-web-share, merged separately.
export function PageShareModal(props: Props) {
  const { isOpen, onClose } = props;

  return (
    <ModalCore isOpen={isOpen} handleClose={onClose} position={EModalPosition.CENTER} width={EModalWidth.XL}>
      <div className="space-y-2 p-5">
        <h3 className="text-16 font-medium text-primary">Share page</h3>
        <p className="text-13 text-tertiary">Sharing options are coming soon.</p>
      </div>
    </ModalCore>
  );
}
