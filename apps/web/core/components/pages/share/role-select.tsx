/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TPageShareRole } from "@plane/types";
import { CustomSelect } from "@plane/ui";
// local imports
import { ROLE_LABELS, ROLES } from "./constants";

type Props = {
  value: TPageShareRole;
  onChange: (role: TPageShareRole) => void;
  buttonClassName: string;
  disabled?: boolean;
};

export function PageShareRoleSelect(props: Props) {
  const { value, onChange, buttonClassName, disabled } = props;

  return (
    <CustomSelect
      value={value}
      onChange={onChange}
      label={ROLE_LABELS[value]}
      buttonClassName={buttonClassName}
      disabled={disabled}
    >
      {ROLES.map((role) => (
        <CustomSelect.Option key={role} value={role}>
          {ROLE_LABELS[role]}
        </CustomSelect.Option>
      ))}
    </CustomSelect>
  );
}
