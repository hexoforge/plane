/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { X } from "lucide-react";
// plane imports
import type { TPageShare, TPageShareRole } from "@plane/types";
import { Avatar } from "@plane/ui";
import { getFileURL } from "@plane/utils";
// hooks
import { useMember } from "@/hooks/store/use-member";
// local imports
import { ROLE_LABELS } from "./constants";
import { PageShareRoleSelect } from "./role-select";

type TOwnerRowProps = {
  ownerId: string;
  currentUserId: string | undefined;
};

const PageShareOwnerRow = observer(function PageShareOwnerRow(props: TOwnerRowProps) {
  const { ownerId, currentUserId } = props;
  const { getUserDetails } = useMember();
  const ownerDetails = getUserDetails(ownerId);

  if (!ownerDetails) return null;

  return (
    <div className="flex items-center justify-between gap-2 py-1.5">
      <div className="flex items-center gap-2">
        <Avatar name={ownerDetails.display_name} src={getFileURL(ownerDetails.avatar_url)} />
        <span className="text-13 text-primary">
          {ownerDetails.display_name}
          {ownerId === currentUserId && " (you)"}
        </span>
      </div>
      <span className="text-13 text-secondary">Owner</span>
    </div>
  );
});

type TShareRowProps = {
  share: TPageShare;
  isOwner: boolean;
  isPending: boolean;
  onRoleChange: (share: TPageShare, role: TPageShareRole) => void;
  onRemove: (share: TPageShare) => void;
};

const PageShareRow = observer(function PageShareRow(props: TShareRowProps) {
  const { share, isOwner, isPending, onRoleChange, onRemove } = props;
  const { getUserDetails } = useMember();
  const memberDetails = getUserDetails(share.user);

  return (
    <div className="flex items-center justify-between gap-2 py-1.5">
      <div className="flex items-center gap-2">
        <Avatar name={memberDetails?.display_name} src={getFileURL(memberDetails?.avatar_url ?? "")} />
        <span className="text-13 text-primary">{memberDetails?.display_name ?? "Unknown member"}</span>
      </div>
      {isOwner ? (
        <div className="flex items-center gap-1">
          <PageShareRoleSelect
            value={share.role}
            onChange={(role) => onRoleChange(share, role)}
            buttonClassName="!px-2 !py-1 hover:bg-surface-1"
            disabled={isPending}
          />
          <button
            type="button"
            aria-label="Remove access"
            className="grid place-items-center rounded p-1 text-secondary hover:bg-surface-1 disabled:opacity-50"
            onClick={() => onRemove(share)}
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
});

type Props = {
  shares: TPageShare[];
  ownerId: string | undefined;
  currentUserId: string | undefined;
  isOwner: boolean;
  pendingShareIds: Set<string>;
  onRoleChange: (share: TPageShare, role: TPageShareRole) => void;
  onRemove: (share: TPageShare) => void;
};

export function PageShareList(props: Props) {
  const { shares, ownerId, currentUserId, isOwner, pendingShareIds, onRoleChange, onRemove } = props;

  return (
    <div className="space-y-1">
      {ownerId && <PageShareOwnerRow ownerId={ownerId} currentUserId={currentUserId} />}
      {shares.length === 0 && <p className="py-2 text-13 text-secondary">No one else has access to this page yet.</p>}
      {shares.map((share) => (
        <PageShareRow
          key={share.id}
          share={share}
          isOwner={isOwner}
          isPending={pendingShareIds.has(share.id)}
          onRoleChange={onRoleChange}
          onRemove={onRemove}
        />
      ))}
    </div>
  );
}
