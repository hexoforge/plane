/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useMemo, useState } from "react";
import { observer } from "mobx-react";
import { useParams, useSearchParams } from "next/navigation";
import Link from "next/link";
import { ChevronLeft, MessageSquare } from "lucide-react";
// plane imports
import { Button, getButtonStyling } from "@plane/propel/button";
import { WikiIcon } from "@plane/propel/icons";
import { Breadcrumbs, Header } from "@plane/ui";
import { cn, getPageName } from "@plane/utils";
// components
import { BreadcrumbLink } from "@/components/common/breadcrumb-link";
import { PageHeaderActions } from "@/components/pages/header/actions";
import { PageSyncingBadge } from "@/components/pages/header/syncing-badge";
import { PageShareModal } from "@/components/pages/share/share-modal";
// hooks
import { EPageStoreType, usePage } from "@/hooks/store";
import { useAppRouter } from "@/hooks/use-app-router";
import { useQueryParams } from "@/hooks/use-query-params";

export const WIKI_COMMENTS_QUERY_PARAM = "comments";

export const WikiPageDetailsHeader = observer(function WikiPageDetailsHeader() {
  const { workspaceSlug, pageId } = useParams();
  const searchParams = useSearchParams();
  const router = useAppRouter();
  const { updateQueryParams } = useQueryParams();
  const [isShareOpen, setIsShareOpen] = useState(false);
  const page = usePage({ pageId: pageId?.toString() ?? "", storeType: EPageStoreType.WIKI });
  const isCommentsOpen = searchParams.get(WIKI_COMMENTS_QUERY_PARAM) === "open";

  const toggleComments = () => {
    const updatedRoute = isCommentsOpen
      ? updateQueryParams({ paramsToRemove: [WIKI_COMMENTS_QUERY_PARAM] })
      : updateQueryParams({ paramsToAdd: { [WIKI_COMMENTS_QUERY_PARAM]: "open" } });
    router.push(updatedRoute);
  };

  const wikiBreadcrumb = useMemo(
    () => (
      <BreadcrumbLink
        label="Wiki"
        href={`/${workspaceSlug}/wiki/`}
        icon={<WikiIcon className="h-4 w-4 text-tertiary" />}
      />
    ),
    [workspaceSlug]
  );

  const pageBreadcrumb = useMemo(
    () => <BreadcrumbLink label={getPageName(page?.name)} href={`/${workspaceSlug}/wiki/${pageId}`} isLast />,
    [page?.name, workspaceSlug, pageId]
  );

  if (!page) return null;

  return (
    <Header>
      {page.id && (
        <PageShareModal
          workspaceSlug={workspaceSlug?.toString() ?? ""}
          pageId={page.id}
          isOpen={isShareOpen}
          onClose={() => setIsShareOpen(false)}
        />
      )}
      <Header.LeftItem>
        <Link
          href={`/${workspaceSlug}/wiki`}
          className={cn(getButtonStyling("ghost", "sm"), "md:hidden")}
          aria-label="All wiki pages"
        >
          <ChevronLeft className="size-3.5" />
        </Link>
        <Breadcrumbs>
          <Breadcrumbs.Item component={wikiBreadcrumb} />
          <Breadcrumbs.Item component={pageBreadcrumb} isLast />
        </Breadcrumbs>
      </Header.LeftItem>
      <Header.RightItem>
        <PageSyncingBadge syncStatus={page.isSyncingWithServer} />
        <Button variant="ghost" size="sm" onClick={toggleComments}>
          <MessageSquare className="size-3.5" />
        </Button>
        <Button variant="secondary" size="sm" onClick={() => setIsShareOpen(true)}>
          Share
        </Button>
        <PageHeaderActions page={page} storeType={EPageStoreType.WIKI} />
      </Header.RightItem>
    </Header>
  );
});
