/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TPageShareRole } from "@plane/types";

export const ROLE_LABELS: Record<TPageShareRole, string> = {
  0: "Can view",
  1: "Can comment",
  2: "Can edit",
};

export const ROLES = Object.keys(ROLE_LABELS).map(Number) as TPageShareRole[];
