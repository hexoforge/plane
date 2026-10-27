/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useCallback, useEffect, useMemo } from "react";
import { observer } from "mobx-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import useSWR from "swr";
// plane imports
import { getButtonStyling } from "@plane/propel/button";
import type { TSearchEntityRequestPayload, TWebhookConnectionQueryParams } from "@plane/types";
import { EFileAssetType } from "@plane/types";
import { cn } from "@plane/utils";
// components
import { LogoSpinner } from "@/components/common/logo-spinner";
import { PageHead } from "@/components/core/page-title";
import type { TPageRootConfig, TPageRootHandlers } from "@/components/pages/editor/page-root";
import { PageRoot } from "@/components/pages/editor/page-root";
import { WikiCommentsPanel } from "@/components/wiki/comments/comments-panel";
// hooks
import { useEditorConfig } from "@/hooks/editor";
import { EPageStoreType, usePage, usePageStore } from "@/hooks/store";
import { useEditorAsset } from "@/hooks/store/use-editor-asset";
import { useWorkspace } from "@/hooks/store/use-workspace";
import { useAppRouter } from "@/hooks/use-app-router";
// services
import { WikiService } from "@/services/wiki.service";
import { WorkspaceService } from "@/services/workspace.service";
import { WIKI_COMMENTS_QUERY_PARAM } from "./header";
import type { Route } from "./+types/page";

const workspaceService = new WorkspaceService();
const wikiService = new WikiService();
const storeType = EPageStoreType.WIKI;

function WikiPageDetailsPage({ params }: Route.ComponentProps) {
  const router = useAppRouter();
  const { workspaceSlug, pageId } = params;
  const searchParams = useSearchParams();
  const isCommentsOpen = searchParams.get(WIKI_COMMENTS_QUERY_PARAM) === "open";
  // store hooks
  const { createPage, fetchPageDetails } = usePageStore(storeType);
  const page = usePage({ pageId, storeType });
  const { getWorkspaceBySlug } = useWorkspace();
  const { uploadEditorAsset, duplicateEditorAsset } = useEditorAsset();
  // derived values
  const workspaceId = workspaceSlug ? (getWorkspaceBySlug(workspaceSlug)?.id ?? "") : "";
  const { canCurrentUserAccessPage, id, name, updateDescription } = page ?? {};
  // entity search handler
  const fetchEntityCallback = useCallback(
    async (payload: TSearchEntityRequestPayload) => await workspaceService.searchEntity(workspaceSlug, payload),
    [workspaceSlug]
  );
  const { getEditorFileHandlers } = useEditorConfig();
  const { error: pageDetailsError } = useSWR(`WIKI_PAGE_DETAILS_${pageId}`, () =>
    fetchPageDetails(workspaceSlug, pageId)
  );

  const pageRootHandlers: TPageRootHandlers = useMemo(
    () => ({
      create: createPage,
      fetchAllVersions: async (versionsPageId) => await wikiService.fetchAllVersions(workspaceSlug, versionsPageId),
      fetchDescriptionBinary: async () => {
        if (!id) return;
        return await wikiService.fetchDescriptionBinary(workspaceSlug, id);
      },
      fetchEntity: fetchEntityCallback,
      fetchVersionDetails: async (versionsPageId, versionId) =>
        await wikiService.fetchVersionById(workspaceSlug, versionsPageId, versionId),
      restoreVersion: async (versionsPageId, versionId) =>
        await wikiService.restoreVersion(workspaceSlug, versionsPageId, versionId),
      getRedirectionLink: (redirectPageId) =>
        redirectPageId ? `/${workspaceSlug}/wiki/${redirectPageId}` : `/${workspaceSlug}/wiki`,
      updateDescription: updateDescription ?? (async () => {}),
    }),
    [createPage, fetchEntityCallback, id, updateDescription, workspaceSlug]
  );

  const pageRootConfig: TPageRootConfig = useMemo(
    () => ({
      fileHandler: getEditorFileHandlers({
        uploadFile: async (blockId, file) => {
          const { asset_id } = await uploadEditorAsset({
            blockId,
            data: { entity_identifier: id ?? "", entity_type: EFileAssetType.PAGE_DESCRIPTION },
            file,
            workspaceSlug,
          });
          return asset_id;
        },
        duplicateFile: async (assetId: string) => {
          const { asset_id } = await duplicateEditorAsset({
            assetId,
            entityId: id,
            entityType: EFileAssetType.PAGE_DESCRIPTION,
            workspaceSlug,
          });
          return asset_id;
        },
        workspaceId,
        workspaceSlug,
      }),
    }),
    [getEditorFileHandlers, workspaceId, workspaceSlug, uploadEditorAsset, id, duplicateEditorAsset]
  );

  const webhookConnectionParams: TWebhookConnectionQueryParams = useMemo(
    () => ({
      documentType: "workspace_page",
      workspaceSlug,
    }),
    [workspaceSlug]
  );

  useEffect(() => {
    if (page?.deleted_at && page?.id) {
      router.push(pageRootHandlers.getRedirectionLink());
    }
  }, [page?.deleted_at, page?.id, router, pageRootHandlers]);

  if ((!page || !id) && !pageDetailsError)
    return (
      <div className="grid size-full place-items-center">
        <LogoSpinner />
      </div>
    );

  if (pageDetailsError || !canCurrentUserAccessPage)
    return (
      <div className="flex h-full w-full flex-col items-center justify-center">
        <h3 className="text-center text-16 font-semibold">Page not found</h3>
        <p className="mt-3 text-center text-13 text-secondary">
          The page you are trying to access doesn{"'"}t exist or you don{"'"}t have permission to view it.
        </p>
        <Link href={`/${workspaceSlug}/wiki`} className={cn(getButtonStyling("secondary", "base"), "mt-5")}>
          View wiki
        </Link>
      </div>
    );

  if (!page) return null;

  return (
    <>
      <PageHead title={name} />
      <div className="flex h-full flex-col justify-between">
        <div className="relative flex h-full w-full flex-shrink-0 overflow-hidden">
          <PageRoot
            config={pageRootConfig}
            handlers={pageRootHandlers}
            storeType={storeType}
            page={page}
            webhookConnectionParams={webhookConnectionParams}
            workspaceSlug={workspaceSlug}
          />
          {isCommentsOpen && id && (
            <WikiCommentsPanel
              workspaceSlug={workspaceSlug}
              pageId={id}
              isOpen={isCommentsOpen}
              onClose={() => router.push(`/${workspaceSlug}/wiki/${id}`)}
            />
          )}
        </div>
      </div>
    </>
  );
}

export default observer(WikiPageDetailsPage);
