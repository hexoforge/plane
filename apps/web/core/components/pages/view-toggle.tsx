/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { List, ListTree } from "lucide-react";
// plane imports
import { Tooltip } from "@plane/propel/tooltip";
import { cn } from "@plane/utils";
// hooks
import type { TPagesViewMode } from "@/hooks/use-project-pages-view";

type Props = {
  viewMode: TPagesViewMode;
  onChange: (mode: TPagesViewMode) => void;
};

const VIEW_OPTIONS: { key: TPagesViewMode; label: string; icon: typeof List }[] = [
  { key: "list", label: "List view", icon: List },
  { key: "tree", label: "Tree view", icon: ListTree },
];

export function PagesViewToggle(props: Props) {
  const { viewMode, onChange } = props;

  return (
    <div className="flex items-center gap-1 rounded-md bg-layer-3 p-1">
      {VIEW_OPTIONS.map((option) => (
        <Tooltip key={option.key} tooltipContent={option.label}>
          <button
            type="button"
            aria-label={option.label}
            className={cn(
              "grid h-5.5 w-7 place-items-center rounded-sm transition-all hover:bg-layer-transparent-hover",
              { "bg-layer-transparent-active hover:bg-layer-transparent-active": viewMode === option.key }
            )}
            onClick={() => onChange(option.key)}
          >
            <option.icon className={cn("size-3.5", viewMode === option.key ? "text-primary" : "text-secondary")} />
          </button>
        </Tooltip>
      ))}
    </div>
  );
}
