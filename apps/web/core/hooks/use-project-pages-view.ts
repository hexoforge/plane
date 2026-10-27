/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useSearchParams } from "next/navigation";
// hooks
import { useAppRouter } from "@/hooks/use-app-router";
import { useQueryParams } from "@/hooks/use-query-params";

export type TPagesViewMode = "list" | "tree";

export const useProjectPagesView = () => {
  const searchParams = useSearchParams();
  const router = useAppRouter();
  const { updateQueryParams } = useQueryParams();

  const viewMode: TPagesViewMode = searchParams.get("view") === "tree" ? "tree" : "list";
  const activeCollectionId = searchParams.get("collection");

  const setViewMode = (mode: TPagesViewMode) => {
    router.push(updateQueryParams({ paramsToAdd: { view: mode } }));
  };

  const setActiveCollectionId = (collectionId: string | null) => {
    if (collectionId) router.push(updateQueryParams({ paramsToAdd: { collection: collectionId } }));
    else router.push(updateQueryParams({ paramsToRemove: ["collection"] }));
  };

  return { viewMode, setViewMode, activeCollectionId, setActiveCollectionId };
};
