/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
// plane imports
import { Button } from "@plane/propel/button";
import type { TPageShareRole } from "@plane/types";
import { EModalPosition, EModalWidth, Loader, ModalCore } from "@plane/ui";
// hooks
import { useUser } from "@/hooks/store/user";
// local imports
import { PageShareAddMemberRow } from "./add-member-row";
import { PageShareList } from "./share-list";
import { usePageShares } from "./use-page-shares";
import { useShareMemberOptions } from "./use-share-member-options";

type Props = {
  workspaceSlug: string;
  projectId?: string;
  pageId: string;
  isOpen: boolean;
  onClose: () => void;
};

export const PageShareModal = observer(function PageShareModal(props: Props) {
  const { workspaceSlug, projectId, pageId, isOpen, onClose } = props;
  // states
  const [newMemberId, setNewMemberId] = useState<string | undefined>(undefined);
  const [newMemberRole, setNewMemberRole] = useState<TPageShareRole>(0);
  // store hooks
  const { data: currentUser } = useUser();
  const { shares, ownerId, pendingShareIds, isAdding, addShare, changeRole, removeShare } = usePageShares({
    workspaceSlug,
    projectId,
    pageId,
    isOpen,
  });
  const { memberOptions, getMemberDisplay } = useShareMemberOptions({ projectId, ownerId, shares });
  // derived values
  const isOwner = !!currentUser?.id && !!ownerId && currentUser.id === ownerId;

  const resetNewMember = () => {
    setNewMemberId(undefined);
    setNewMemberRole(0);
  };

  const handleClose = () => {
    resetNewMember();
    onClose();
  };

  const handleAddShare = async () => {
    if (!newMemberId) return;
    if (await addShare(newMemberId, newMemberRole)) resetNewMember();
  };

  return (
    <ModalCore isOpen={isOpen} handleClose={handleClose} position={EModalPosition.CENTER} width={EModalWidth.XXL}>
      <div className="space-y-0 px-5 py-4">
        <h3 className="text-16 leading-6 font-medium text-primary">Share page</h3>
        <p className="mt-1 text-13 text-secondary">
          {isOwner
            ? "Invite workspace members to view, comment on or edit this page."
            : "People with access to this page."}
        </p>
      </div>
      <div className="max-h-96 space-y-4 overflow-y-auto px-5 pb-5">
        {shares === undefined ? (
          <Loader className="space-y-3">
            <Loader.Item height="36px" />
            <Loader.Item height="36px" />
          </Loader>
        ) : (
          <>
            {isOwner && (
              <PageShareAddMemberRow
                memberId={newMemberId}
                memberLabel={newMemberId ? getMemberDisplay(newMemberId)?.display_name : undefined}
                role={newMemberRole}
                options={memberOptions}
                isAdding={isAdding}
                onMemberChange={setNewMemberId}
                onRoleChange={setNewMemberRole}
                onSubmit={handleAddShare}
              />
            )}
            <PageShareList
              shares={shares}
              ownerId={ownerId}
              currentUserId={currentUser?.id}
              isOwner={isOwner}
              pendingShareIds={pendingShareIds}
              onRoleChange={changeRole}
              onRemove={removeShare}
            />
          </>
        )}
      </div>
      <div className="flex items-center justify-end gap-2 border-t-[0.5px] border-subtle px-5 py-4">
        <Button variant="secondary" size="lg" onClick={handleClose}>
          Done
        </Button>
      </div>
    </ModalCore>
  );
});
