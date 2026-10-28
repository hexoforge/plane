/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { ReactNode } from "react";
// plane imports
import { Button } from "@plane/propel/button";
import type { TPageShareRole } from "@plane/types";
import { CustomSearchSelect } from "@plane/ui";
// local imports
import { PageShareRoleSelect } from "./role-select";

type Props = {
  memberId: string | undefined;
  memberLabel: string | undefined;
  role: TPageShareRole;
  options: { value: string; query: string; content: ReactNode }[];
  isAdding: boolean;
  onMemberChange: (userId: string) => void;
  onRoleChange: (role: TPageShareRole) => void;
  onSubmit: () => void;
};

export function PageShareAddMemberRow(props: Props) {
  const { memberId, memberLabel, role, options, isAdding, onMemberChange, onRoleChange, onSubmit } = props;

  return (
    <div className="flex items-center gap-2">
      <div className="flex-1">
        <CustomSearchSelect
          value={memberId}
          label={memberId ? memberLabel : <span className="text-secondary">Add a member</span>}
          buttonClassName="!px-3 !py-2 bg-surface-1 w-full"
          options={options}
          onChange={onMemberChange}
          maxHeight="md"
        />
      </div>
      <PageShareRoleSelect value={role} onChange={onRoleChange} buttonClassName="!px-3 !py-2 bg-surface-1" />
      <Button variant="primary" size="lg" onClick={onSubmit} disabled={!memberId || isAdding}>
        {isAdding ? "Sharing..." : "Share"}
      </Button>
    </div>
  );
}
