/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { EModalPosition, EModalWidth, ModalCore } from "@plane/ui";

export type TPageShareModalProps = {
  workspaceSlug: string;
  projectId?: string;
  pageId: string;
  isOpen: boolean;
  onClose: () => void;
};

/**
 * shortcut: placeholder until feat/wiki-web-share lands the real sharing UI, then this file is replaced wholesale
 */
export function PageShareModal(props: TPageShareModalProps) {
  const { isOpen, onClose } = props;

  return (
    <ModalCore isOpen={isOpen} handleClose={onClose} position={EModalPosition.TOP} width={EModalWidth.XL}>
      <div className="space-y-2 p-5">
        <h3 className="text-lg font-medium text-primary">Share page</h3>
        <p className="text-sm text-tertiary">Sharing is coming soon.</p>
      </div>
    </ModalCore>
  );
}
