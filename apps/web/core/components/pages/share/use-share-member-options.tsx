/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { ReactNode } from "react";
// plane imports
import type { TPageShare } from "@plane/types";
import { Avatar } from "@plane/ui";
import { getFileURL } from "@plane/utils";
// hooks
import { useMember } from "@/hooks/store/use-member";

type Params = {
  projectId?: string;
  ownerId?: string;
  shares?: TPageShare[];
};

type TMemberOption = { value: string; query: string; content: ReactNode };

export const useShareMemberOptions = (params: Params) => {
  const { projectId, ownerId, shares } = params;
  const {
    workspace: { workspaceMemberIds, getWorkspaceMemberDetails },
    project: { getProjectMemberIds, getProjectMemberDetails },
  } = useMember();

  const getMemberDisplay = (userId: string) =>
    projectId ? getProjectMemberDetails(userId, projectId)?.member : getWorkspaceMemberDetails(userId)?.member;

  const existingUserIds = new Set([ownerId, ...(shares ?? []).map((s) => s.user)].filter(Boolean) as string[]);
  const candidateMemberIds = (projectId ? getProjectMemberIds(projectId, false) : workspaceMemberIds) ?? [];

  const memberOptions = candidateMemberIds.flatMap((userId): TMemberOption[] => {
    if (existingUserIds.has(userId)) return [];
    const member = getMemberDisplay(userId);
    if (!member) return [];
    return [
      {
        value: userId,
        query: member.display_name,
        content: (
          <div className="flex items-center gap-2">
            <Avatar name={member.display_name} src={getFileURL(member.avatar_url)} size="sm" />
            {member.display_name}
          </div>
        ),
      },
    ];
  });

  return { memberOptions, getMemberDisplay };
};
