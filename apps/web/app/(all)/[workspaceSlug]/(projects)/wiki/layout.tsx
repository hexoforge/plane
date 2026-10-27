/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { Outlet } from "react-router";
// plane imports
import { EUserPermissions, EUserPermissionsLevel } from "@plane/constants";
// components
import { NotAuthorizedView } from "@/components/auth-screens/not-authorized-view";
import { WikiSidebarRoot } from "@/components/wiki/sidebar/wiki-sidebar-root";
// hooks
import { useUserPermissions } from "@/hooks/store/user";
// local imports
import type { Route } from "./+types/layout";

export default function WikiLayout({ params }: Route.ComponentProps) {
  const { workspaceSlug } = params;
  const { allowPermissions } = useUserPermissions();

  const canAccessWiki = allowPermissions(
    [EUserPermissions.ADMIN, EUserPermissions.MEMBER],
    EUserPermissionsLevel.WORKSPACE,
    workspaceSlug
  );

  if (!canAccessWiki) return <NotAuthorizedView />;

  return (
    <div className="flex h-full w-full overflow-hidden">
      <WikiSidebarRoot workspaceSlug={workspaceSlug} />
      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <Outlet />
      </div>
    </div>
  );
}
