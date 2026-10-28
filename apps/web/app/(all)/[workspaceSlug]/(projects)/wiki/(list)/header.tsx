/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useMemo } from "react";
import { useParams } from "next/navigation";
// plane imports
import { WikiIcon } from "@plane/propel/icons";
import { Breadcrumbs, Header } from "@plane/ui";
// components
import { BreadcrumbLink } from "@/components/common/breadcrumb-link";

export function WikiListHeader() {
  const { workspaceSlug } = useParams();

  const wikiBreadcrumb = useMemo(
    () => (
      <BreadcrumbLink
        label="Wiki"
        href={`/${workspaceSlug}/wiki/`}
        icon={<WikiIcon className="h-4 w-4 text-tertiary" />}
        isLast
      />
    ),
    [workspaceSlug]
  );

  return (
    <Header>
      <Header.LeftItem>
        <Breadcrumbs>
          <Breadcrumbs.Item component={wikiBreadcrumb} isLast />
        </Breadcrumbs>
      </Header.LeftItem>
    </Header>
  );
}
