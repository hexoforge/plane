/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useParams } from "next/navigation";
import { Outlet } from "react-router";
// plane imports
import { EUserPermissions, EUserPermissionsLevel } from "@plane/constants";
import { cn } from "@plane/utils";
// components
import { NotAuthorizedView } from "@/components/auth-screens/not-authorized-view";
import { WikiSidebarRoot } from "@/components/wiki/sidebar/wiki-sidebar-root";
// hooks
import { useUserPermissions } from "@/hooks/store/user";
// local imports
import type { Route } from "./+types/layout";

export default function WikiLayout({ params }: Route.ComponentProps) {
  const { workspaceSlug } = params;
  const { pageId } = useParams();
  const { allowPermissions } = useUserPermissions();
  const isPageOpen = !!pageId;

  const canAccessWiki = allowPermissions(
    [EUserPermissions.ADMIN, EUserPermissions.MEMBER],
    EUserPermissionsLevel.WORKSPACE,
    workspaceSlug
  );

  if (!canAccessWiki) return <NotAuthorizedView />;

  return (
    <div className="flex h-full w-full overflow-hidden">
      <div className={cn("h-full w-full md:block md:w-64 md:flex-shrink-0", isPageOpen ? "hidden" : "block")}>
        <WikiSidebarRoot workspaceSlug={workspaceSlug} />
      </div>
      <div className={cn("min-w-0 flex-1 flex-col overflow-hidden md:flex", isPageOpen ? "flex" : "hidden")}>
        <Outlet />
      </div>
    </div>
  );
}
