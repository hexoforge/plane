/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useRef, useState } from "react";
import { observer } from "mobx-react";
import useSWR from "swr";
import { X } from "lucide-react";
// plane imports
import type { EditorRefApi } from "@plane/editor";
import { useTranslation } from "@plane/i18n";
import { IconButton } from "@plane/propel/icon-button";
import { TrashIcon } from "@plane/propel/icons";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { EFileAssetType } from "@plane/types";
import { Avatar, Loader } from "@plane/ui";
import { calculateTimeAgo, cn, isCommentEmpty } from "@plane/utils";
// components
import { LiteTextEditor } from "@/components/editor/lite-text/editor";
import { SimpleEmptyState } from "@/components/empty-state/simple-empty-state-root";
// hooks
import { EPageStoreType, usePageStore } from "@/hooks/store";
import { useEditorAsset } from "@/hooks/store/use-editor-asset";
import { useMember } from "@/hooks/store/use-member";
import { useWorkspace } from "@/hooks/store/use-workspace";

type Props = {
  workspaceSlug: string;
  pageId: string;
  isOpen: boolean;
  onClose: () => void;
};

export const WikiCommentsPanel = observer(function WikiCommentsPanel(props: Props) {
  const { workspaceSlug, pageId, isOpen, onClose } = props;
  const { t } = useTranslation();
  const editorRef = useRef<EditorRefApi>(null);
  const [draft, setDraft] = useState<{ json: object; html: string } | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { comments, fetchComments, createComment, deleteComment } = usePageStore(EPageStoreType.WIKI);
  const { getUserDetails } = useMember();
  const { getWorkspaceBySlug } = useWorkspace();
  const { uploadEditorAsset, duplicateEditorAsset } = useEditorAsset();
  const workspaceId = getWorkspaceBySlug(workspaceSlug)?.id ?? "";

  const { isLoading } = useSWR(isOpen ? `WIKI_PAGE_COMMENTS_${pageId}` : null, () =>
    fetchComments(workspaceSlug, pageId)
  );

  const pageComments = (comments[pageId] ?? []).filter((comment) => !comment.parent);

  const handleSubmit = async () => {
    if (!draft || isCommentEmpty(draft.html)) return;
    setIsSubmitting(true);
    try {
      await createComment(workspaceSlug, pageId, { comment_html: draft.html, comment_json: draft.json });
      editorRef.current?.clearEditor();
      setDraft(null);
    } catch {
      setToast({ type: TOAST_TYPE.ERROR, title: "Error!", message: "Comment could not be posted." });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async (commentId: string) => {
    try {
      await deleteComment(workspaceSlug, pageId, commentId);
    } catch {
      setToast({ type: TOAST_TYPE.ERROR, title: "Error!", message: "Comment could not be deleted." });
    }
  };

  if (!isOpen) return null;

  return (
    <div className="flex h-full w-80 flex-shrink-0 flex-col border-l border-subtle bg-surface-1">
      <div className="flex items-center justify-between border-b border-subtle px-4 py-3">
        <h3 className="text-14 font-medium text-primary">Comments</h3>
        <IconButton variant="ghost" size="sm" icon={X} onClick={onClose} aria-label="Close comments" />
      </div>
      <div className="flex-1 space-y-4 overflow-y-auto px-4 py-4">
        {isLoading ? (
          <Loader className="space-y-3">
            <Loader.Item height="48px" />
            <Loader.Item height="48px" />
          </Loader>
        ) : pageComments.length === 0 ? (
          <SimpleEmptyState title="No comments yet" description="Start the discussion on this page." />
        ) : (
          pageComments.map((comment) => {
            const actor = getUserDetails(comment.actor);
            return (
              <div key={comment.id} className="group/comment flex gap-2">
                <Avatar size="sm" name={actor?.display_name} src={actor?.avatar_url ?? undefined} className="mt-0.5" />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-13 font-medium text-primary">
                      {actor?.display_name ?? t("common.deactivated_user")}
                    </span>
                    <span className="text-11 text-placeholder">{calculateTimeAgo(comment.created_at)}</span>
                    <IconButton
                      variant="ghost"
                      size="sm"
                      icon={TrashIcon}
                      onClick={() => handleDelete(comment.id)}
                      className="ml-auto opacity-0 group-hover/comment:opacity-100"
                      aria-label="Delete comment"
                    />
                  </div>
                  <div
                    className={cn("prose-sm mt-1 max-w-none text-13 text-secondary prose")}
                    // comment_html is sanitized server-side before storage
                    dangerouslySetInnerHTML={{ __html: comment.comment_html }}
                  />
                </div>
              </div>
            );
          })
        )}
      </div>
      <div className="border-t border-subtle p-3">
        <LiteTextEditor
          ref={editorRef}
          id={`wiki-comment-${pageId}`}
          workspaceSlug={workspaceSlug}
          workspaceId={workspaceId}
          editable
          variant="lite"
          initialValue=""
          placeholder="Add a comment..."
          uploadFile={async (blockId, file) => {
            const { asset_id } = await uploadEditorAsset({
              blockId,
              data: { entity_identifier: pageId, entity_type: EFileAssetType.PAGE_DESCRIPTION },
              file,
              workspaceSlug,
            });
            return asset_id;
          }}
          duplicateFile={async (assetId: string) => {
            const { asset_id } = await duplicateEditorAsset({
              assetId,
              entityId: pageId,
              entityType: EFileAssetType.PAGE_DESCRIPTION,
              workspaceSlug,
            });
            return asset_id;
          }}
          onChange={(json, html) => setDraft({ json, html })}
          onEnterKeyPress={handleSubmit}
          isSubmitting={isSubmitting}
        />
      </div>
    </div>
  );
});
