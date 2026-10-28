# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import re

WORK_ITEM_REF_PATTERN = re.compile(r"\b([A-Za-z][A-Za-z0-9]{0,11})-(\d+)\b")
CLOSING_KEYWORD_PATTERN = re.compile(r"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s+#(\d+)\b", re.IGNORECASE)


def extract_refs(text: str | None, identifiers) -> list[tuple[str, int]]:
    """Find PROJ-123 style work item references in text.

    Only refs whose identifier (case insensitive) is in `identifiers` are
    returned, as (identifier, sequence_id) pairs with the identifier
    normalized to uppercase. Used for matching branch names, PR/issue
    titles and bodies against known project identifiers.
    """
    if not text:
        return []

    identifier_set = {identifier.upper() for identifier in identifiers}
    refs = []
    seen = set()
    for identifier, number in WORK_ITEM_REF_PATTERN.findall(text):
        normalized = identifier.upper()
        key = (normalized, number)
        if normalized in identifier_set and key not in seen:
            seen.add(key)
            refs.append((normalized, int(number)))
    return refs


def extract_closing_refs(text: str | None) -> list[int]:
    """Find 'fixes/closes/resolves #N' references to a GitHub issue number."""
    if not text:
        return []
    return [int(number) for number in dict.fromkeys(CLOSING_KEYWORD_PATTERN.findall(text))]
