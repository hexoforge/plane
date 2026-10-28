/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useCallback } from "react";
import { observer } from "mobx-react";
import { ListFilter } from "lucide-react";
// plane imports
import { useTranslation } from "@plane/i18n";
import type { TPageFilterProps, TPageNavigationTabs } from "@plane/types";
import { Header, EHeaderVariant } from "@plane/ui";
import { calculateTotalFilters } from "@plane/utils";
// components
import { FiltersDropdown } from "@/components/issues/issue-layouts/filters";
// hooks
import { useMember } from "@/hooks/store/use-member";
import { usePageStore } from "@/hooks/store";
import type { EPageStoreType } from "@/hooks/store";
import { useProjectPagesView } from "@/hooks/use-project-pages-view";
// local imports
import { PageCollectionSwitcher } from "../collections/switcher";
import { PageAppliedFiltersList } from "../list/applied-filters/root";
import { PageFiltersSelection } from "../list/filters/root";
import { PageOrderByDropdown } from "../list/order-by";
import { PageSearchInput } from "../list/search-input";
import { PageTabNavigation } from "../list/tab-navigation";
import { PagesViewToggle } from "../view-toggle";

type Props = {
  pageType: TPageNavigationTabs;
  projectId: string;
  storeType: EPageStoreType.PROJECT;
  workspaceSlug: string;
};

export const PagesListHeaderRoot = observer(function PagesListHeaderRoot(props: Props) {
  const { pageType, projectId, storeType, workspaceSlug } = props;
  const { t } = useTranslation();
  // store hooks
  const { filters, updateFilters, clearAllFilters } = usePageStore(storeType);
  const {
    workspace: { workspaceMemberIds },
  } = useMember();
  const { viewMode, setViewMode, activeCollectionId, setActiveCollectionId } = useProjectPagesView();

  const handleRemoveFilter = useCallback(
    (key: keyof TPageFilterProps, value: string | null) => {
      let newValues = filters.filters?.[key];

      if (key === "favorites") newValues = !!value;
      if (Array.isArray(newValues)) {
        if (!value) newValues = [];
        else newValues = newValues.filter((val) => val !== value);
      }

      updateFilters("filters", { [key]: newValues });
    },
    [filters.filters, updateFilters]
  );

  const isFiltersApplied = calculateTotalFilters(filters?.filters ?? {}) !== 0;

  return (
    <>
      <Header variant={EHeaderVariant.SECONDARY}>
        <Header.LeftItem>
          <PageTabNavigation workspaceSlug={workspaceSlug} projectId={projectId} pageType={pageType} />
          {pageType !== "archived" && (
            <div className="flex items-center gap-2 pl-2">
              <PageCollectionSwitcher
                workspaceSlug={workspaceSlug}
                projectId={projectId}
                activeCollectionId={activeCollectionId}
                onChange={setActiveCollectionId}
              />
              <PagesViewToggle viewMode={viewMode} onChange={setViewMode} />
            </div>
          )}
        </Header.LeftItem>
        <Header.RightItem className="items-center">
          <PageSearchInput
            searchQuery={filters.searchQuery}
            updateSearchQuery={(val) => updateFilters("searchQuery", val)}
          />
          <PageOrderByDropdown
            sortBy={filters.sortBy}
            sortKey={filters.sortKey}
            onChange={(val) => {
              if (val.key) updateFilters("sortKey", val.key);
              if (val.order) updateFilters("sortBy", val.order);
            }}
          />
          <FiltersDropdown
            icon={<ListFilter className="h-3 w-3" />}
            title={t("common.filters")}
            placement="bottom-end"
            isFiltersApplied={isFiltersApplied}
          >
            <PageFiltersSelection
              filters={filters}
              handleFiltersUpdate={updateFilters}
              memberIds={workspaceMemberIds ?? undefined}
            />
          </FiltersDropdown>
        </Header.RightItem>
      </Header>
      {calculateTotalFilters(filters?.filters ?? {}) !== 0 && (
        <Header variant={EHeaderVariant.TERNARY}>
          <PageAppliedFiltersList
            appliedFilters={filters.filters ?? {}}
            handleClearAllFilters={clearAllFilters}
            handleRemoveFilter={handleRemoveFilter}
            alwaysAllowEditing
          />
        </Header>
      )}
    </>
  );
});
