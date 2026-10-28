/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useId } from "react";
import { Search, X } from "lucide-react";

type Props = {
  value: string;
  onChange: (value: string) => void;
};

export function WikiSidebarSearch(props: Props) {
  const { value, onChange } = props;
  const inputId = useId();

  return (
    <div className="flex min-w-0 flex-1 items-center gap-2 rounded-md border border-subtle px-2 py-1.5">
      <Search className="size-3.5 flex-shrink-0 text-placeholder" />
      <label htmlFor={inputId} className="sr-only">
        Search wiki
      </label>
      <input
        id={inputId}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Search wiki"
        className="w-full min-w-0 border-none bg-transparent text-13 text-primary placeholder:text-placeholder focus:outline-none"
      />
      {value && (
        <button type="button" onClick={() => onChange("")} aria-label="Clear search">
          <X className="size-3.5 text-placeholder" />
        </button>
      )}
    </div>
  );
}
