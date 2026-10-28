/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect, useReducer, useState } from "react";
// plane imports
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import type { TPageShare, TPageShareRole } from "@plane/types";
// services
import pageShareService from "@/services/page-share.service";

type Params = {
  workspaceSlug: string;
  projectId?: string;
  pageId: string;
  isOpen: boolean;
};

const showErrorToast = (error: unknown, fallback: string) => {
  setToast({
    type: TOAST_TYPE.ERROR,
    title: "Error!",
    message: (error as { error?: string })?.error ?? fallback,
  });
};

type TState = { shares: TPageShare[] | undefined; ownerId: string | undefined };

type TAction =
  | { type: "loading" }
  | { type: "loaded"; shares: TPageShare[]; ownerId: string | undefined }
  | { type: "load-failed" }
  | { type: "added"; share: TPageShare }
  | { type: "updated"; share: TPageShare }
  | { type: "removed"; shareId: string };

const reducer = (state: TState, action: TAction): TState => {
  switch (action.type) {
    case "loading":
      return { ...state, shares: undefined };
    case "loaded":
      return { shares: action.shares, ownerId: action.ownerId };
    case "load-failed":
      return { ...state, shares: [] };
    case "added":
      return { ...state, shares: [...(state.shares ?? []), action.share] };
    case "updated":
      return { ...state, shares: state.shares?.map((s) => (s.id === action.share.id ? action.share : s)) };
    case "removed":
      return { ...state, shares: state.shares?.filter((s) => s.id !== action.shareId) };
  }
};

export const usePageShares = (params: Params) => {
  const { workspaceSlug, projectId, pageId, isOpen } = params;
  const [{ shares, ownerId }, dispatch] = useReducer(reducer, { shares: undefined, ownerId: undefined });
  const [pendingShareIds, setPendingShareIds] = useState<Set<string>>(new Set());
  const [isAdding, setIsAdding] = useState(false);

  useEffect(() => {
    if (!isOpen) return;
    dispatch({ type: "loading" });
    Promise.all([
      pageShareService.list(workspaceSlug, pageId, projectId),
      pageShareService.fetchPageOwner(workspaceSlug, pageId, projectId),
    ])
      .then(([sharesResponse, owner]) => {
        dispatch({ type: "loaded", shares: sharesResponse, ownerId: owner });
        return null;
      })
      .catch((error: { error?: string }) => {
        dispatch({ type: "load-failed" });
        showErrorToast(error, "Failed to load page shares. Please try again.");
      });
  }, [isOpen, workspaceSlug, pageId, projectId]);

  const markPending = (shareId: string) => setPendingShareIds((prev) => new Set(prev).add(shareId));

  const unmarkPending = (shareId: string) =>
    setPendingShareIds((prev) => {
      const next = new Set(prev);
      next.delete(shareId);
      return next;
    });

  const addShare = async (userId: string, role: TPageShareRole): Promise<boolean> => {
    setIsAdding(true);
    try {
      const share = await pageShareService.create(workspaceSlug, pageId, { user: userId, role }, projectId);
      dispatch({ type: "added", share });
      setToast({ type: TOAST_TYPE.SUCCESS, title: "Success!", message: "Page shared successfully." });
      return true;
    } catch (error: unknown) {
      showErrorToast(error, "Failed to share the page. Please try again.");
      return false;
    } finally {
      setIsAdding(false);
    }
  };

  const changeRole = async (share: TPageShare, role: TPageShareRole) => {
    markPending(share.id);
    try {
      const updated = await pageShareService.update(workspaceSlug, pageId, share.id, { role }, projectId);
      dispatch({ type: "updated", share: updated });
    } catch (error: unknown) {
      showErrorToast(error, "Failed to update access. Please try again.");
    } finally {
      unmarkPending(share.id);
    }
  };

  const removeShare = async (share: TPageShare) => {
    markPending(share.id);
    try {
      await pageShareService.remove(workspaceSlug, pageId, share.id, projectId);
      dispatch({ type: "removed", shareId: share.id });
      setToast({ type: TOAST_TYPE.SUCCESS, title: "Success!", message: "Access removed." });
    } catch (error: unknown) {
      showErrorToast(error, "Failed to remove access. Please try again.");
      unmarkPending(share.id);
    }
  };

  return { shares, ownerId, pendingShareIds, isAdding, addShare, changeRole, removeShare };
};
