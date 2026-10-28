/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { ReactNode } from "react";
import { observer } from "mobx-react";
// plane imports
import { Breadcrumbs } from "@plane/ui";
// components
import { BreadcrumbLink } from "@/components/common/breadcrumb-link";
import { SettingsPageHeader } from "@/components/settings/page-header";

type Props = {
  label: string;
  icon: ReactNode;
};

export const SettingsBreadcrumbHeader = observer(function SettingsBreadcrumbHeader({ label, icon }: Props) {
  return (
    <SettingsPageHeader
      leftItem={
        <div className="flex items-center gap-2">
          <Breadcrumbs>
            <Breadcrumbs.Item component={<BreadcrumbLink label={label} icon={icon} />} />
          </Breadcrumbs>
        </div>
      }
    />
  );
});
