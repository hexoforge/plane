/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useMemo, useState } from "react";
// plane imports
import type { TWikiTreeNode } from "@plane/types";

export const useWikiSidebarExpansion = (searchQuery: string, treeNodes: TWikiTreeNode[]) => {
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
  const [syncedVisibleIds, setSyncedVisibleIds] = useState<Set<string> | null>(null);

  const toggleExpand = (id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  // auto-expand ancestors of nodes matching the active search query
  const visibleIds = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    if (!query) return null;
    const byId = new Map(treeNodes.map((node) => [node.id, node]));
    const matched = treeNodes.filter((node) => (node.name ?? "").toLowerCase().includes(query));
    const visible = new Set<string>();
    matched.forEach((node) => {
      let current: typeof node | undefined = node;
      while (current) {
        visible.add(current.id);
        current = current.parent ? byId.get(current.parent) : undefined;
      }
    });
    return visible;
  }, [searchQuery, treeNodes]);

  if (visibleIds !== syncedVisibleIds) {
    setSyncedVisibleIds(visibleIds);
    if (visibleIds) setExpandedIds(new Set(visibleIds));
  }

  return { expandedIds, toggleExpand, visibleIds };
};
