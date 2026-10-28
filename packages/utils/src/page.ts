/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { sortBy } from "lodash-es";
// plane imports
import type {
  TPage,
  TPageFilterProps,
  TPageFiltersSortBy,
  TPageFiltersSortKey,
  TPageNavigationTabs,
} from "@plane/types";
// local imports
import { getDate } from "./datetime";
import { satisfiesDateFilter } from "./filter";

/**
 * @description filters pages based on the page type
 * @param {TPageNavigationTabs} pageType
 * @param {TPage[]} pages
 * @returns {TPage[]}
 */
export const filterPagesByPageType = (pageType: TPageNavigationTabs, pages: TPage[]): TPage[] =>
  pages.filter((page) => {
    if (pageType === "public") return page.access === 0 && !page.archived_at;
    if (pageType === "private") return page.access === 1 && !page.archived_at;
    if (pageType === "archived") return page.archived_at;
    return true;
  });

/**
 * @description orders pages based on their status
 * @param {TPage[]} pages
 * @param {TPageFiltersSortKey | undefined} sortByKey
 * @param {TPageFiltersSortBy} sortByOrder
 * @returns {TPage[]}
 */
export const orderPages = (
  pages: TPage[],
  sortByKey: TPageFiltersSortKey | undefined,
  sortByOrder: TPageFiltersSortBy
): TPage[] => {
  let orderedPages: TPage[] = [];
  if (pages.length === 0 || !sortByKey) return [];

  if (sortByKey === "name") {
    orderedPages = sortBy(pages, [(m) => m.name?.toLowerCase()]);
    if (sortByOrder === "desc") orderedPages = orderedPages.toReversed();
  }
  if (sortByKey === "created_at") {
    orderedPages = sortBy(pages, [(m) => m.created_at]);
    if (sortByOrder === "desc") orderedPages = orderedPages.toReversed();
  }
  if (sortByKey === "updated_at") {
    orderedPages = sortBy(pages, [(m) => m.updated_at]);
    if (sortByOrder === "desc") orderedPages = orderedPages.toReversed();
  }

  return orderedPages;
};

/**
 * @description filters pages based on the filters
 * @param {TPage} page
 * @param {TPageFilterProps | undefined} filters
 * @returns {boolean}
 */
export const shouldFilterPage = (page: TPage, filters: TPageFilterProps | undefined): boolean => {
  let fallsInFilters = true;
  Object.keys(filters ?? {}).forEach((key) => {
    const filterKey = key as keyof TPageFilterProps;
    if (filterKey === "created_by" && filters?.created_by && filters.created_by.length > 0)
      fallsInFilters = fallsInFilters && filters.created_by.includes(`${page.owned_by}`);
    if (filterKey === "created_at" && filters?.created_at && filters.created_at.length > 0) {
      const createdDate = getDate(page.created_at);
      filters?.created_at.forEach((dateFilter) => {
        fallsInFilters = fallsInFilters && !!createdDate && satisfiesDateFilter(createdDate, dateFilter);
      });
    }
  });
  if (filters?.favorites && !page.is_favorite) fallsInFilters = false;

  return fallsInFilters;
};

/**
 * @description returns the name of the project after checking for untitled page
 * @param {string | undefined} name
 * @returns {string}
 */
export const getPageName = (name: string | undefined) => {
  if (name === undefined) return "";
  if (!name || name.trim() === "") return "Untitled";
  return name;
};

/**
 * @description returns true if the page belongs to the given collection, falling back
 * pages with no collection into the project's default (General) collection
 */
export const pageBelongsToCollection = (
  page: Pick<TPage, "collection">,
  collectionId: string,
  isDefaultCollection: boolean
): boolean => {
  if (isDefaultCollection) return !page.collection || page.collection === collectionId;
  return page.collection === collectionId;
};

export type TPageTreeNode = { id: string; children: TPageTreeNode[] };

type TTreeSource = Pick<TPage, "id" | "parent" | "sort_order">;

const sortBySortOrder = (pages: TTreeSource[]) =>
  [...pages].toSorted((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0));

/**
 * @description builds a nested id tree from a flat list of pages using the parent field.
 * returns ids rather than page data so callers can keep reading the live (observable) page instance.
 * shortcut: a parent cycle (shouldn't happen, the API rejects it) falls the node back to root instead of looping
 */
export const buildPageTree = (pages: TTreeSource[]): TPageTreeNode[] => {
  const idSet = new Set(pages.map((page) => page.id).filter((id): id is string => !!id));
  const childrenByParent = new Map<string, TTreeSource[]>();

  pages.forEach((page) => {
    const parentKey = page.parent && idSet.has(page.parent) && page.parent !== page.id ? page.parent : "__root__";
    const siblings = childrenByParent.get(parentKey) ?? [];
    siblings.push(page);
    childrenByParent.set(parentKey, siblings);
  });

  const buildNodes = (parentKey: string, ancestors: Set<string>): TPageTreeNode[] =>
    sortBySortOrder(childrenByParent.get(parentKey) ?? [])
      .filter((page): page is TTreeSource & { id: string } => !!page.id && !ancestors.has(page.id))
      .map((page) => ({
        id: page.id,
        children: buildNodes(page.id, new Set(ancestors).add(page.id)),
      }));

  return buildNodes("__root__", new Set());
};
