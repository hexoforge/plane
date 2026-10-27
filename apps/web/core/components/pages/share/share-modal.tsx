/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect, useState } from "react";
import { observer } from "mobx-react";
import { X } from "lucide-react";
// plane imports
import { Button } from "@plane/propel/button";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import type { TPageShare, TPageShareRole } from "@plane/types";
import { Avatar, CustomSearchSelect, CustomSelect, EModalPosition, EModalWidth, Loader, ModalCore } from "@plane/ui";
import { getFileURL } from "@plane/utils";
// hooks
import { useMember } from "@/hooks/store/use-member";
import { useUser } from "@/hooks/store/user";
// services
import pageShareService from "@/services/page-share.service";

type Props = {
  workspaceSlug: string;
  projectId?: string;
  pageId: string;
  isOpen: boolean;
  onClose: () => void;
};

const ROLE_LABELS: Record<TPageShareRole, string> = {
  0: "Can view",
  1: "Can comment",
  2: "Can edit",
};

export const PageShareModal = observer(function PageShareModal(props: Props) {
  const { workspaceSlug, projectId, pageId, isOpen, onClose } = props;
  // states
  const [shares, setShares] = useState<TPageShare[] | undefined>(undefined);
  const [ownerId, setOwnerId] = useState<string | undefined>(undefined);
  const [pendingShareIds, setPendingShareIds] = useState<Set<string>>(new Set());
  const [newMemberId, setNewMemberId] = useState<string | undefined>(undefined);
  const [newMemberRole, setNewMemberRole] = useState<TPageShareRole>(0);
  const [isAdding, setIsAdding] = useState(false);
  // store hooks
  const { data: currentUser } = useUser();
  const {
    workspace: { workspaceMemberIds, getWorkspaceMemberDetails },
    project: { getProjectMemberIds, getProjectMemberDetails },
    getUserDetails,
  } = useMember();

  useEffect(() => {
    if (!isOpen) return;
    setShares(undefined);
    Promise.all([
      pageShareService.list(workspaceSlug, pageId, projectId),
      pageShareService.fetchPageOwner(workspaceSlug, pageId, projectId),
    ])
      .then(([sharesResponse, owner]) => {
        setShares(sharesResponse);
        setOwnerId(owner);
        return null;
      })
      .catch((error: { error?: string }) => {
        setShares([]);
        setToast({
          type: TOAST_TYPE.ERROR,
          title: "Error!",
          message: error?.error ?? "Failed to load page shares. Please try again.",
        });
      });
  }, [isOpen, workspaceSlug, pageId, projectId]);

  const handleClose = () => {
    setNewMemberId(undefined);
    setNewMemberRole(0);
    onClose();
  };

  const isOwner = !!currentUser?.id && !!ownerId && currentUser.id === ownerId;

  const getMemberDisplay = (userId: string) =>
    projectId ? getProjectMemberDetails(userId, projectId)?.member : getWorkspaceMemberDetails(userId)?.member;

  const handleAddShare = async () => {
    if (!newMemberId) return;
    setIsAdding(true);
    try {
      const share = await pageShareService.create(
        workspaceSlug,
        pageId,
        { user: newMemberId, role: newMemberRole },
        projectId
      );
      setShares((prev) => [...(prev ?? []), share]);
      setNewMemberId(undefined);
      setNewMemberRole(0);
      setToast({ type: TOAST_TYPE.SUCCESS, title: "Success!", message: "Page shared successfully." });
    } catch (error: unknown) {
      const err = error as { error?: string };
      setToast({
        type: TOAST_TYPE.ERROR,
        title: "Error!",
        message: err?.error ?? "Failed to share the page. Please try again.",
      });
    } finally {
      setIsAdding(false);
    }
  };

  const handleRoleChange = async (share: TPageShare, role: TPageShareRole) => {
    setPendingShareIds((prev) => new Set(prev).add(share.id));
    try {
      const updated = await pageShareService.update(workspaceSlug, pageId, share.id, { role }, projectId);
      setShares((prev) => prev?.map((s) => (s.id === share.id ? updated : s)));
    } catch (error: unknown) {
      const err = error as { error?: string };
      setToast({
        type: TOAST_TYPE.ERROR,
        title: "Error!",
        message: err?.error ?? "Failed to update access. Please try again.",
      });
    } finally {
      setPendingShareIds((prev) => {
        const next = new Set(prev);
        next.delete(share.id);
        return next;
      });
    }
  };

  const handleRemoveShare = async (share: TPageShare) => {
    setPendingShareIds((prev) => new Set(prev).add(share.id));
    try {
      await pageShareService.remove(workspaceSlug, pageId, share.id, projectId);
      setShares((prev) => prev?.filter((s) => s.id !== share.id));
      setToast({ type: TOAST_TYPE.SUCCESS, title: "Success!", message: "Access removed." });
    } catch (error: unknown) {
      const err = error as { error?: string };
      setToast({
        type: TOAST_TYPE.ERROR,
        title: "Error!",
        message: err?.error ?? "Failed to remove access. Please try again.",
      });
      setPendingShareIds((prev) => {
        const next = new Set(prev);
        next.delete(share.id);
        return next;
      });
    }
  };

  const existingUserIds = new Set([ownerId, ...(shares ?? []).map((s) => s.user)].filter(Boolean) as string[]);
  const candidateMemberIds = (projectId ? getProjectMemberIds(projectId, false) : workspaceMemberIds) ?? [];
  const memberOptions = candidateMemberIds
    .filter((userId) => !existingUserIds.has(userId))
    .map((userId) => {
      const member = getMemberDisplay(userId);
      if (!member) return null;
      return {
        value: userId,
        query: member.display_name,
        content: (
          <div className="flex items-center gap-2">
            <Avatar name={member.display_name} src={getFileURL(member.avatar_url)} size="sm" />
            {member.display_name}
          </div>
        ),
      };
    })
    .filter((option) => !!option) as
    | {
        value: string;
        query: string;
        content: React.ReactNode;
      }[]
    | undefined;

  const ownerDetails = ownerId ? getUserDetails(ownerId) : undefined;

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
              <div className="flex items-center gap-2">
                <div className="flex-1">
                  <CustomSearchSelect
                    value={newMemberId}
                    label={
                      newMemberId ? (
                        getMemberDisplay(newMemberId)?.display_name
                      ) : (
                        <span className="text-secondary">Add a member</span>
                      )
                    }
                    buttonClassName="!px-3 !py-2 bg-surface-1 w-full"
                    options={memberOptions}
                    onChange={(value: string) => setNewMemberId(value)}
                    maxHeight="md"
                  />
                </div>
                <CustomSelect
                  value={newMemberRole}
                  onChange={(value: TPageShareRole) => setNewMemberRole(value)}
                  label={ROLE_LABELS[newMemberRole]}
                  buttonClassName="!px-3 !py-2 bg-surface-1"
                >
                  {(Object.keys(ROLE_LABELS) as unknown as TPageShareRole[]).map((role) => (
                    <CustomSelect.Option key={role} value={Number(role) as TPageShareRole}>
                      {ROLE_LABELS[Number(role) as TPageShareRole]}
                    </CustomSelect.Option>
                  ))}
                </CustomSelect>
                <Button variant="primary" size="lg" onClick={handleAddShare} disabled={!newMemberId || isAdding}>
                  {isAdding ? "Sharing..." : "Share"}
                </Button>
              </div>
            )}

            <div className="space-y-1">
              {ownerDetails && (
                <div className="flex items-center justify-between gap-2 py-1.5">
                  <div className="flex items-center gap-2">
                    <Avatar name={ownerDetails.display_name} src={getFileURL(ownerDetails.avatar_url)} />
                    <span className="text-13 text-primary">
                      {ownerDetails.display_name}
                      {ownerId === currentUser?.id && " (you)"}
                    </span>
                  </div>
                  <span className="text-13 text-secondary">Owner</span>
                </div>
              )}
              {shares?.length === 0 && (
                <p className="py-2 text-13 text-secondary">No one else has access to this page yet.</p>
              )}
              {shares?.map((share) => {
                const memberDetails = getUserDetails(share.user);
                const isPending = pendingShareIds.has(share.id);
                return (
                  <div key={share.id} className="flex items-center justify-between gap-2 py-1.5">
                    <div className="flex items-center gap-2">
                      <Avatar name={memberDetails?.display_name} src={getFileURL(memberDetails?.avatar_url ?? "")} />
                      <span className="text-13 text-primary">{memberDetails?.display_name ?? "Unknown member"}</span>
                    </div>
                    {isOwner ? (
                      <div className="flex items-center gap-1">
                        <CustomSelect
                          value={share.role}
                          onChange={(value: TPageShareRole) => handleRoleChange(share, value)}
                          label={ROLE_LABELS[share.role]}
                          buttonClassName="!px-2 !py-1 hover:bg-surface-1"
                          disabled={isPending}
                        >
                          {(Object.keys(ROLE_LABELS) as unknown as TPageShareRole[]).map((role) => (
                            <CustomSelect.Option key={role} value={Number(role) as TPageShareRole}>
                              {ROLE_LABELS[Number(role) as TPageShareRole]}
                            </CustomSelect.Option>
                          ))}
                        </CustomSelect>
                        <button
                          type="button"
                          aria-label="Remove access"
                          className="grid place-items-center rounded p-1 text-secondary hover:bg-surface-1 disabled:opacity-50"
                          onClick={() => handleRemoveShare(share)}
                          disabled={isPending}
                        >
                          <X className="size-3.5" />
                        </button>
                      </div>
                    ) : (
                      <span className="text-13 text-secondary">{ROLE_LABELS[share.role]}</span>
                    )}
                  </div>
                );
              })}
            </div>
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
