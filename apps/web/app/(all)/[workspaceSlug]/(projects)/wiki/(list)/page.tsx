/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// plane imports
import { WikiIcon } from "@plane/propel/icons";
// components
import { PageHead } from "@/components/core/page-title";
import { SimpleEmptyState } from "@/components/empty-state/simple-empty-state-root";

export default function WikiHomePage() {
  return (
    <>
      <PageHead title="Wiki" />
      <div className="flex h-full w-full items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <WikiIcon className="size-10 text-placeholder" />
          <SimpleEmptyState
            title="Select or create a page"
            description="Pick a page from the sidebar or start a new one in any collection."
            size="lg"
          />
        </div>
      </div>
    </>
  );
}
